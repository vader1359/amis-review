from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from secrets import token_urlsafe
from typing import Protocol
from uuid import uuid4

from openpyxl import load_workbook

from .engine import build
from .persistence import PsiMemoryRepository, PsiMemoryStore, UploadAuthorizationError, UploadValidationError, week_to_period
from .release_adapter import storage_delete, storage_download, storage_signed_download, storage_upload
from .release_gate import ReleaseGateDecision, evaluate_gate

class ReleaseRepository(Protocol):
    def insert(self, table: str, row: dict[str, str | int | list[str] | dict[str, str] | None], auth_token: str = "") -> None: ...
    def upload(self, path: str, content: bytes, auth_token: str = "") -> None: ...
    def lookup(self, table: str, filters: dict[str, str], auth_token: str = "") -> list[dict[str, str | int | list[str] | dict[str, str] | None]]: ...


@dataclass(frozen=True, slots=True)
class ReleaseRequest:
    reporting_period: str
    actor_id: str
    team_id: str = "team-a"


@dataclass(frozen=True, slots=True)
class ReleaseConfig:
    max_source_age_days: int = 30
    as_of: date = field(default_factory=date.today)


@dataclass(frozen=True, slots=True)
class ReleaseRecord:
    id: str
    draft_id: str
    object_path: str
    checksum_sha256: str
    source_snapshot_ids: tuple[str, ...]
    status: str
    signed_url: str | None

    def to_json(self) -> dict[str, str | list[str] | None]:
        return asdict(self)


class ReleaseGateError(UploadValidationError):
    """Raised when a release cannot satisfy the explicit release gate."""

    def __init__(self, message: str, reasons: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.reasons = reasons or (message,)


class PsiReleaseService:
    def __init__(self, store: PsiMemoryStore, config: ReleaseConfig | None = None) -> None:
        self.store = store
        self.config = config or ReleaseConfig()
        self.tokens = getattr(store, "release_tokens", {})
        store.release_tokens = self.tokens

    def generate(self, request: ReleaseRequest, auth_token: str = "") -> ReleaseRecord:
        snapshots = self._selected_snapshots(request, auth_token)
        decision = self._gate(snapshots, request, auth_token)
        if not decision.allowed:
            raise ReleaseGateError("; ".join(decision.messages), decision.messages)
        files = {str(row["original_filename"]): self._source_bytes(str(row["object_path"]), auth_token) for row in snapshots}
        for row in snapshots:
            if sha256(files[str(row["original_filename"])]).hexdigest() != str(row["checksum_sha256"]):
                raise ReleaseGateError("selected source checksum changed", ("selected source checksum changed",))
        result = build(files)
        if result.gaps:
            raise ReleaseGateError("schema results are not clean", ("schema results are not clean",))
        try:
            load_workbook(io.BytesIO(result.xlsx), data_only=False).close()
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
            raise ReleaseGateError("generated workbook is not openable", ("generated workbook is not openable",)) from error
        checksum = sha256(result.xlsx).hexdigest()
        release_id = str(uuid4())
        draft_id = str(uuid4())
        repository = self.store.repository
        source_ids = tuple(str(row["id"]) for row in snapshots)
        context = self._context(request, snapshots, release_id, auth_token)
        draft_path = f"{context['team_id']}/{request.reporting_period}/{draft_id}/PSI Draft.xlsx"
        object_path = f"{context['team_id']}/{request.reporting_period}/{release_id}/PSI Final.xlsx"
        try:
            # The draft and published artifact are identical in this MVP
            # (there is no approval step). Upload both objects concurrently so
            # storage latency does not consume the serverless request budget.
            with ThreadPoolExecutor(max_workers=2) as pool:
                draft_upload = pool.submit(self._upload, "psi-draft", draft_path, result.xlsx, auth_token)
                release_upload = pool.submit(self._upload, "psi-release", object_path, result.xlsx, auth_token)
                draft_upload.result()
                release_upload.result()
            repository.insert("psi_drafts", {"id": draft_id, "reporting_period_id": context["reporting_period_id"], "reconciliation_run_id": context["reconciliation_run_id"], "rule_version_id": context["rule_version_id"], "status": "approved", "object_path": draft_path, "checksum_sha256": checksum, "created_by": request.actor_id}, auth_token)
            for row in snapshots:
                repository.insert("draft_sources", {"draft_id": draft_id, "source_snapshot_id": str(row["id"]), "source_type": str(row["source_type"])}, auth_token)
        except (OSError, UploadValidationError):
            self._cleanup_attempt(context, draft_path, object_path, draft_id, release_id, auth_token)
            raise
        try:
            repository.insert("psi_releases", {"id": release_id, "psi_draft_id": draft_id, "reporting_period_id": context["reporting_period_id"], "rule_version_id": context["rule_version_id"], "object_path": object_path, "checksum_sha256": checksum, "row_count": int(result.summary.get("Product master rows", 0)), "kpis": {"summary": str(result.summary)}, "approved_by": request.actor_id, "published_by": request.actor_id}, auth_token)
            for row in snapshots:
                repository.insert("release_sources", {"release_id": release_id, "source_snapshot_id": str(row["id"]), "source_type": str(row["source_type"])}, auth_token)
            repository.insert("activity_logs", {"team_id": context["team_id"], "actor_id": request.actor_id, "action": "psi.release.published", "entity_type": "psi_release", "entity_id": release_id, "metadata": {"checksum_sha256": checksum, "source_snapshot_ids": ",".join(source_ids)}}, auth_token)
        except (OSError, UploadValidationError):
            self._cleanup_attempt(context, draft_path, object_path, draft_id, release_id, auth_token)
            raise
        signed_url = self._signed_url(object_path, request.actor_id, auth_token)
        return ReleaseRecord(release_id, draft_id, object_path, checksum, source_ids, "published", signed_url)

    def local_download(self, token: str, actor_id: str) -> bytes:
        entry = self.tokens.get(token)
        if entry is None or entry[0] != actor_id or entry[2] <= datetime.now(UTC):
            raise UploadAuthorizationError("download authorization is invalid")
        return entry[1]

    def inspect_gate(self, request: ReleaseRequest, auth_token: str = "") -> ReleaseGateDecision:
        return self._gate(self._selected_snapshots(request, auth_token), request, auth_token)

    def _selected_snapshots(self, request: ReleaseRequest, auth_token: str) -> list[dict[str, str | int | list[str] | dict[str, str] | None]]:
        repository = self.store.repository
        if isinstance(repository, PsiMemoryRepository):
            latest = {
                snapshot.source_type: snapshot
                for snapshot in sorted(
                    (
                        snapshot
                        for snapshot in self.store.snapshots
                        if snapshot.team_id == request.team_id
                        and snapshot.reporting_period == request.reporting_period
                        and snapshot.schema_status == "passed"
                    ),
                    key=lambda snapshot: snapshot.version,
                )
            }
            return [{"id": snapshot.id, "source_type": snapshot.source_type, "original_filename": snapshot.original_filename, "object_path": snapshot.object_path, "checksum_sha256": snapshot.checksum_sha256, "data_as_of": snapshot.data_as_of, "schema_status": snapshot.schema_status} for snapshot in latest.values()]
        periods = repository.lookup("reporting_periods", {"period_key": request.reporting_period}, auth_token)
        if not periods:
            raise ReleaseGateError("release context is unavailable")
        selections = repository.lookup("source_selections", {"reporting_period_id": str(periods[0]["id"])}, auth_token)
        return [snapshot for selection in selections for snapshot in repository.lookup("source_snapshots", {"id": str(selection["source_snapshot_id"])}, auth_token)]

    def _gate(self, snapshots: list[dict[str, str | int | list[str] | dict[str, str] | None]], request: ReleaseRequest, auth_token: str) -> ReleaseGateDecision:
        period_id = request.reporting_period
        if not isinstance(self.store.repository, PsiMemoryRepository):
            periods = self.store.repository.lookup("reporting_periods", {"period_key": request.reporting_period}, auth_token)
            period_id = str(periods[0]["id"]) if periods else period_id
        mismatches = [] if "-W" in request.reporting_period else self.store.repository.lookup("mismatches", {"reporting_period_id": period_id}, auth_token)
        if not isinstance(self.store.repository, PsiMemoryRepository):
            suppressed = {
                str(row.get("fingerprint"))
                for row in self.store.repository.lookup("known_issues", {}, auth_token)
                if str(row.get("status")) in {"known", "approved"}
            }
            mismatches = [row for row in mismatches if str(row.get("fingerprint")) not in suppressed]
        as_of = date.fromisoformat(week_to_period(request.reporting_period)[1]) if "-W" in request.reporting_period else self.config.as_of
        decision = evaluate_gate(snapshots, mismatches, as_of, self.config.max_source_age_days)
        return decision

    def _source_bytes(self, path: str, auth_token: str) -> bytes:
        repository = self.store.repository
        if isinstance(repository, PsiMemoryRepository):
            return repository.objects[path]
        if hasattr(repository, "url"):
            return storage_download(repository, "psi-source", path, auth_token)
        downloader = getattr(repository, "download")
        return downloader(path, auth_token)

    def _signed_url(self, path: str, actor_id: str, auth_token: str) -> str | None:
        repository = self.store.repository
        if isinstance(repository, PsiMemoryRepository):
            token = token_urlsafe(24)
            self.tokens[token] = (actor_id, repository.objects[path], datetime.now(UTC) + timedelta(minutes=5))
            return "/api/download/" + token
        if hasattr(repository, "url"):
            return storage_signed_download(repository, "psi-release", path, 300, auth_token)
        signer = getattr(repository, "signed_download")
        return signer(path, 300, auth_token)

    def _upload(self, bucket: str, path: str, content: bytes, token: str) -> None:
        repository = self.store.repository
        if isinstance(repository, PsiMemoryRepository):
            repository.upload(path, content, token)
        else:
            storage_upload(repository, bucket, path, content, token)

    def _delete(self, bucket: str, path: str, token: str) -> None:
        repository = self.store.repository
        if isinstance(repository, PsiMemoryRepository):
            repository.objects.pop(path, None)
        elif hasattr(repository, "url"):
            storage_delete(repository, bucket, path, token)

    def _cleanup_attempt(self, context: dict[str, str], draft_path: str, final_path: str, draft_id: str, release_id: str, token: str) -> None:
        for bucket, path in (("psi-release", final_path), ("psi-draft", draft_path)):
            try:
                self._delete(bucket, path, token)
            except OSError:
                pass
        repository = self.store.repository
        for table, key, value in (
            ("release_sources", "release_id", release_id),
            ("activity_logs", "entity_id", release_id),
            ("psi_releases", "id", release_id),
            ("draft_sources", "draft_id", draft_id),
            ("psi_drafts", "id", draft_id),
            ("reconciliation_run_sources", "reconciliation_run_id", context["reconciliation_run_id"]),
            ("reconciliation_runs", "id", context["reconciliation_run_id"]),
        ):
            try:
                repository.delete(table, {key: value}, token)
            except OSError:
                pass

    def _context(self, request: ReleaseRequest, snapshots: list[dict[str, str | int | list[str] | dict[str, str] | None]], run_id: str, token: str) -> dict[str, str]:
        if isinstance(self.store.repository, PsiMemoryRepository):
            return {"team_id": request.team_id, "reporting_period_id": request.reporting_period, "rule_version_id": "local-rule", "reconciliation_run_id": run_id}
        period = self.store.repository.lookup("reporting_periods", {"period_key": request.reporting_period}, token)
        rules = self.store.repository.lookup("rule_versions", {"version": "1"}, token)
        memberships = self.store.repository.lookup("team_memberships", {"team_id": request.team_id, "profile_id": request.actor_id}, token)
        if not period or not rules or not memberships:
            raise ReleaseGateError("release context is unavailable")
        context = {"team_id": str(memberships[0]["team_id"]), "reporting_period_id": str(period[0]["id"]), "rule_version_id": str(rules[0]["id"]), "reconciliation_run_id": run_id}
        completed_at = datetime.now(UTC).isoformat()
        self.store.repository.insert("reconciliation_runs", {"id": run_id, "reporting_period_id": context["reporting_period_id"], "started_by": request.actor_id, "rule_version_id": context["rule_version_id"], "status": "completed", "started_at": completed_at, "completed_at": completed_at}, token)
        for row in snapshots:
            self.store.repository.insert("reconciliation_run_sources", {"reconciliation_run_id": run_id, "source_snapshot_id": str(row["id"]), "source_type": str(row["source_type"])}, token)
        return context
