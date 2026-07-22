from __future__ import annotations

import json
from email.parser import BytesParser
from pathlib import PurePosixPath
from urllib.error import HTTPError
from email.policy import default
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from psi_engine.release import ReleaseRequest
from psi_engine.release_adapter import storage_delete, storage_download, storage_signed_download
from psi_engine.persistence import (
    ALLOWED_CONTENT_TYPE,
    PsiMemoryRepository,
    SupabaseRepository,
    UploadAuthorizationError,
    UploadRequest,
    UploadValidationError,
    week_to_period,
)
from psi_engine.sources import OPTIONAL_SOURCES, REQUIRED_SOURCES, UPLOAD_SOURCES


class WeeklyRoutesMixin:
    def weekly_status(self) -> None:
        query = self._query()
        if isinstance(self.store.repository, SupabaseRepository):
            token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            try:
                actor_id = self.store.repository.authenticated_actor(token)
                memberships = self.store.repository.lookup("team_memberships", {"profile_id": actor_id}, token)
                if not memberships:
                    raise UploadAuthorizationError("team membership is required")
                team_id = str(memberships[0]["team_id"])
                period_key = query["week"][0]
                periods = self.store.repository.lookup("reporting_periods", {"period_key": period_key}, token)
                if not periods:
                    raise UploadValidationError("reporting period is unavailable")
                period_id = str(periods[0]["id"])
                selections = self.store.repository.lookup("source_selections", {"reporting_period_id": period_id}, token)
                snapshots = [
                    snapshot
                    for selection in selections
                    for snapshot in self.store.repository.lookup("source_snapshots", {"id": str(selection["source_snapshot_id"])}, token)
                ]
                latest = {str(snapshot["source_type"]): snapshot for snapshot in snapshots}
                files = {
                    source: {
                        "status": "uploaded",
                        "version": latest[source].get("version"),
                        "snapshot_id": latest[source].get("id"),
                        "filename": latest[source].get("original_filename"),
                    } if source in latest else {"status": "missing", "version": None, "snapshot_id": None, "filename": None}
                    for source in UPLOAD_SOURCES
                }
                mismatches = self.store.repository.lookup("mismatches", {"reporting_period_id": period_id}, token)
                suppressed = {
                    str(row.get("fingerprint"))
                    for row in self.store.repository.lookup("known_issues", {}, token)
                    if str(row.get("status")) in {"known", "approved"}
                }
                active_mismatches = [
                    row for row in mismatches
                    if str(row.get("status")) not in {"known", "resolved", "ignored"}
                    and str(row.get("fingerprint")) not in suppressed
                ]
                detailed_mismatches = []
                for row in active_mismatches:
                    details = row.get("values_by_source") if isinstance(row.get("values_by_source"), dict) else {}
                    detailed_mismatches.append({
                        "id": row.get("id"), "source_type": row.get("source_type"), "record_key": row.get("record_key"),
                        "severity": row.get("severity"), "status": row.get("status"), "file": details.get("file", ""),
                        "sheet": details.get("sheet", ""), "row": details.get("row", ""), "code": details.get("code", ""),
                        "description": details.get("description", ""), "issue": details.get("issue", ""),
                    })
                sources_ready = all(source in latest for source in REQUIRED_SOURCES)
                gate = self.release_service.inspect_gate(ReleaseRequest(period_key, actor_id, team_id), token)
                releases = self.store.repository.lookup("psi_releases", {"reporting_period_id": period_id}, token)
                latest_release = max(releases, key=lambda row: str(row.get("published_at", "")), default=None)
                download_url = storage_signed_download(self.store.repository, "psi-release", str(latest_release["object_path"]), 300, token) if latest_release else None
                payload = {
                    "team_id": team_id, "week": period_key, "files": files,
                    "required_sources": list(REQUIRED_SOURCES),
                    "optional_sources": list(OPTIONAL_SOURCES),
                    "owned_sources": list(UPLOAD_SOURCES), "ready": sources_ready,
                    "release_allowed": gate.allowed, "gate_reasons": list(gate.messages),
                    "mismatches": detailed_mismatches, "download_url": download_url,
                }
            except KeyError as error:
                self.send(400, ("required query parameter is missing: " + str(error)).encode(), "text/plain")
                return
            except UploadAuthorizationError as error:
                self.send(401, str(error).encode(), "text/plain")
                return
            except UploadValidationError as error:
                self.send(400, str(error).encode(), "text/plain")
                return
            except HTTPError:
                self.send(502, b"Supabase status request failed", "text/plain")
                return
            self.send(200, json.dumps(payload, ensure_ascii=False).encode(), "application/json")
            return
        try:
            payload = self.store.weekly_status(query.get("team", query.get("team_id"))[0], query["week"][0])
        except (KeyError, UploadValidationError) as error:
            self.send(400, str(error).encode(), "text/plain")
            return
        self.send(200, json.dumps(payload, ensure_ascii=False).encode(), "application/json")

    def persist_upload(self) -> None:
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if isinstance(self.store.repository, SupabaseRepository):
            try:
                actor = (self.store.repository.authenticated_actor(token), "")
            except UploadAuthorizationError:
                self.send(401, b"authenticated bearer is required for Supabase uploads", "text/plain")
                return
        else:
            actor = self._actor()
            if actor is None or self.roles.get(token) != "contributor":
                actor = ("anonymous-uploader", "")
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("multipart/form-data") or "boundary=" not in content_type:
            self.send(400, b"multipart/form-data with boundary is required", "text/plain")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        boundary = content_type.split("boundary=", 1)[1].split(";", 1)[0].strip().encode()
        if not body.rstrip().endswith(b"--" + boundary + b"--"):
            self.send(400, b"multipart body is truncated", "text/plain")
            return
        message = BytesParser(policy=default).parsebytes(b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body)
        fields: dict[str, str] = {}
        uploaded: tuple[str, str, bytes] | None = None
        for part in message.iter_parts():
            field = part.get_param("name", header="content-disposition") or ""
            filename = part.get_filename()
            if filename:
                uploaded = (filename, part.get_content_type(), part.get_payload(decode=True))
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                self.send(400, b"malformed multipart field", "text/plain")
                return
            fields[field] = payload.decode("utf-8")
        if uploaded is None:
            self.send(400, b"file is required", "text/plain")
            return
        filename, file_type, content = uploaded
        try:
            week = fields.get("week", fields.get("reporting_period", ""))
            _, week_end = week_to_period(week) if "-W" in week else (week, fields["data_as_of"])
            persisted = self.store.persist(
                UploadRequest(
                    team_id=fields["team_id"], actor_id=actor[0], reporting_period=week,
                    data_as_of=fields.get("data_as_of") or week_end, source_type=fields["source_type"],
                    filename=filename, content=content, content_type=file_type,
                ),
                auth_token=token,
            )
        except KeyError:
            self.send(400, b"required metadata is missing", "text/plain")
            return
        except UploadAuthorizationError as error:
            self.send(403, str(error).encode(), "text/plain")
            return
        except HTTPError as error:
            if error.code in (401, 403):
                self.send(403, b"Supabase persistence is not authorized", "text/plain")
            else:
                self.send(502, b"Supabase persistence request failed", "text/plain")
            return
        except UploadValidationError as error:
            self.send(400, str(error).encode(), "text/plain")
            return
        self.send(201, json.dumps(persisted.to_json(), ensure_ascii=False).encode(), "application/json")

    def persist_staged_upload(self) -> None:
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        repository = self.store.repository
        if not isinstance(repository, SupabaseRepository):
            self.send(400, b"staged upload requires Supabase storage", "text/plain")
            return

        cleanup_path = ""
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 64 * 1024:
                raise UploadValidationError("upload metadata size is invalid")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise UploadValidationError("upload metadata is invalid")

            actor_id = repository.authenticated_actor(token)
            team_id = str(payload["team_id"])
            memberships = repository.lookup(
                "team_memberships", {"profile_id": actor_id, "team_id": team_id}, token
            )
            if not memberships:
                self.send(403, b"team membership is required", "text/plain")
                return

            staging_path = str(payload["staging_path"])
            parsed_path = PurePosixPath(staging_path)
            parts = parsed_path.parts
            if (
                staging_path != parsed_path.as_posix()
                or len(parts) != 3
                or parts[0] != team_id
                or parts[1] != "staging"
                or parsed_path.suffix.lower() != ".xlsx"
            ):
                raise UploadValidationError("staging_path is invalid")
            try:
                UUID(parsed_path.stem)
            except ValueError as error:
                raise UploadValidationError("staging_path is invalid") from error

            filename = str(payload["filename"])
            if PurePosixPath(filename).name != filename or not filename.lower().endswith(".xlsx"):
                raise UploadValidationError("filename must be a safe XLSX path component")
            week = str(payload["week"])
            data_as_of = str(payload["data_as_of"])
            source_type = str(payload["source_type"])

            cleanup_path = staging_path
            content = storage_download(repository, "psi-source", staging_path, token)
            persisted = self.store.persist(
                UploadRequest(
                    team_id=team_id,
                    actor_id=actor_id,
                    reporting_period=week,
                    data_as_of=data_as_of,
                    source_type=source_type,
                    filename=filename,
                    content=content,
                    content_type=ALLOWED_CONTENT_TYPE,
                ),
                auth_token=token,
            )
        except KeyError:
            self.send(400, b"required metadata is missing", "text/plain")
            return
        except UploadAuthorizationError as error:
            self.send(401, str(error).encode(), "text/plain")
            return
        except HTTPError as error:
            if error.code in (401, 403):
                self.send(403, b"Supabase persistence is not authorized", "text/plain")
            else:
                self.send(502, b"Supabase staged upload request failed", "text/plain")
            return
        except (TypeError, ValueError, UnicodeDecodeError, UploadValidationError) as error:
            self.send(400, (str(error) or "upload metadata is invalid").encode(), "text/plain")
            return
        finally:
            if cleanup_path:
                try:
                    storage_delete(repository, "psi-source", cleanup_path, token)
                except (HTTPError, OSError, UploadAuthorizationError):
                    pass

        self.send(201, json.dumps(persisted.to_json(), ensure_ascii=False).encode(), "application/json")

    def _query(self) -> dict[str, list[str]]:
        return parse_qs(urlsplit(self.path).query)
