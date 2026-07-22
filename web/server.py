#!/usr/bin/env python3
import json
import os
import sys
from secrets import token_urlsafe
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TypedDict
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psi_engine import build as build_engine
from psi_engine import PsiReleaseService, ReleaseGateError, ReleaseRequest
from psi_engine import classify, norm
from psi_engine.persistence import (
    PsiMemoryRepository,
    PsiMemoryStore,
    UploadAuthorizationError,
    UploadRequest,
    UploadValidationError,
    SupabaseRepository,
    week_to_period,
)
from release_routes import ReleaseRoutesMixin
from weekly_routes import WeeklyRoutesMixin


ROOT = Path(__file__).resolve().parent


def bind_address() -> tuple[str, int]:
    host = os.environ.get("PSI_BIND_HOST") or os.environ.get("APP_HOST") or "127.0.0.1"
    return host, int(os.environ.get("PSI_PORT", "8787"))


class BuildPayload(TypedDict):
    summary: dict[str, int | float]
    issues: list[list[str | int | float | None]]
    gaps: list[list[str | int | float | None]]
    xlsx: bytes


def build(files: dict[str, bytes]) -> BuildPayload:
    result = build_engine(files)
    return {"summary": result.summary, "issues": result.issues, "gaps": result.gaps, "xlsx": result.xlsx}


def build_store() -> PsiMemoryStore:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if bool(url) != bool(key):
        raise UploadValidationError("Supabase server configuration is incomplete")
    return PsiMemoryStore(SupabaseRepository(url, key)) if url and key else PsiMemoryStore()


class H(WeeklyRoutesMixin, ReleaseRoutesMixin, BaseHTTPRequestHandler):
    last = b""
    store = build_store()
    actors: dict[str, tuple[str, str]] = {}
    roles: dict[str, str] = {}
    release_service = PsiReleaseService(store)

    def send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        request_path = urlsplit(self.path).path
        if request_path == "/api/config":
            self.public_config()
            return
        if request_path == "/api/local-preview-session":
            self.local_preview_session()
            return
        if request_path == "/api/dashboard":
            self.dashboard()
            return
        if request_path == "/api/weekly-status":
            self.weekly_status()
            return
        if request_path.startswith("/api/download/"):
            token = request_path.removeprefix("/api/download/")
            actor = self._actor()
            if actor is None and isinstance(self.store.repository, PsiMemoryRepository):
                actor = ("anonymous-uploader", "")
            if actor is None:
                self.send(401, b"unauthorized", "text/plain")
                return
            try:
                content = self.release_service.local_download(token, actor[0])
            except UploadAuthorizationError:
                self.send(403, b"download forbidden", "text/plain")
                return
            self.send(200, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            return
        path = (ROOT / ("index.html" if request_path == "/" else request_path.lstrip("/"))).resolve()
        if ROOT in path.parents and path.is_file():
            content_type = "text/html" if path.suffix == ".html" else "text/css" if path.suffix == ".css" else "text/javascript"
            self.send(200, path.read_bytes(), content_type)
            return
        self.send(404, b"not found", "text/plain")

    def public_config(self) -> None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
        self.send(200, json.dumps({"url": url, "publishable_key": key}).encode(), "application/json")

    def local_preview_session(self) -> None:
        if not isinstance(self.store.repository, PsiMemoryRepository):
            self.send(404, b"not found", "text/plain")
            return
        role = parse_qs(urlsplit(self.path).query).get("role", ["viewer"])[0]
        if role not in {"admin", "reviewer", "viewer", "contributor"}:
            self.send(400, b"preview role is invalid", "text/plain")
            return
        token = "local-preview-" + token_urlsafe(24)
        actor_id = "local-preview-user-" + token.removeprefix("local-preview-")
        self.actors[token] = (actor_id, "team-a")
        self.roles[token] = role
        if role == "contributor" and hasattr(self.store, "actor_teams"):
            self.store.actor_teams[actor_id] = {"team-a"}
        self.send(200, json.dumps({"token": token, "role": role}).encode(), "application/json")

    def do_POST(self) -> None:
        if self.path == "/api/select":
            self.select_snapshot()
            return
        if self.path == "/api/release":
            self.release()
            return
        if self.path == "/api/persist":
            self.persist_upload()
            return
        if self.path == "/api/weekly-upload":
            self.persist_upload()
            return
        if self.path == "/api/mismatch":
            self.mismatch_action()
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        message = BytesParser(policy=default).parsebytes(
            b"Content-Type: " + self.headers.get("Content-Type", "").encode() + b"\r\n\r\n" + body
        )
        files: dict[str, bytes] = {}
        for part in message.iter_attachments():
            filename = part.get_filename()
            if filename:
                field = part.get_param("name", header="content-disposition") or ""
                files[(field + "__" if field else "") + filename] = part.get_payload(decode=True)
        result = build(files)
        H.last = result["xlsx"]
        response = json.dumps(
            {"summary": result["summary"], "issues": result["issues"], "gaps": result["gaps"]},
            ensure_ascii=False,
        ).encode()
        self.send(200, response, "application/json")

    def _actor(self) -> tuple[str, str] | None:
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        return self.actors.get(token)

    def dashboard(self) -> None:
        actor = self._actor()
        if actor is None and isinstance(self.store.repository, PsiMemoryRepository):
            actor = ("local-viewer", "")
        if actor is None:
            self.send(401, b"unauthorized", "text/plain")
            return
        repository = self.store.repository
        if not isinstance(repository, PsiMemoryRepository):
            self.send(503, b"dashboard unavailable while Supabase session is not configured", "text/plain")
            return
        selected = dict(self.store.selections)
        history = [{"id": s.id, "filename": s.original_filename, "source": s.source_type, "reporting_period": s.reporting_period, "checksum": s.checksum_sha256, "schema_status": s.schema_status, "selected": selected.get((s.reporting_period, s.source_type)) == s.id} for s in self.store.snapshots]
        matrix = [{"team": s.team_id, "source": s.source_type, "reporting_period": s.reporting_period, "status": s.schema_status, "selected": selected.get((s.reporting_period, s.source_type)) == s.id} for s in self.store.snapshots]
        mismatches = []
        for row in self.store.repository.lookup("mismatches", {}):
            item = dict(row)
            item["history"] = self.store.repository.lookup("mismatch_history", {"mismatch_id": str(row.get("id", ""))})
            mismatches.append(item)
        period = next(iter(self.store.selections), ("2026-07", ""))[0]
        gate = self.release_service.inspect_gate(ReleaseRequest(period, actor[0], actor[1]))
        payload = {"latest_final": None, "readiness": "ready" if gate.allowed else "blocked", "release_gate": {"allowed": gate.allowed, "reasons": [{"code": reason.code, "message": reason.message, "blocking": reason.blocking} for reason in gate.reasons]}, "history": history, "matrix": matrix, "mismatches": mismatches, "activity": self.store.activity}
        self.send(200, json.dumps(payload, ensure_ascii=False).encode(), "application/json")

    def mismatch_action(self) -> None:
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if isinstance(self.store.repository, SupabaseRepository):
            try:
                actor_id = self.store.repository.authenticated_actor(token)
                memberships = self.store.repository.lookup("team_memberships", {"profile_id": actor_id}, token)
                if not memberships:
                    raise UploadAuthorizationError("team membership is required")
                actor = (actor_id, str(memberships[0]["team_id"]))
            except UploadAuthorizationError:
                self.send(401, b"unauthorized", "text/plain")
                return
        else:
            actor = self._actor()
            if actor is None:
                self.send(401, b"unauthorized", "text/plain")
                return
            if self.roles.get(token, "viewer") != "reviewer":
                self.send(403, b"reviewer role required", "text/plain")
                return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            mismatch_id = str(payload["mismatch_id"])
            to_status = str(payload["to_status"])
            comment = str(payload.get("comment", ""))
            evidence = payload.get("evidence", {})
            if not isinstance(evidence, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in evidence.items()):
                raise ValueError
            if to_status not in {"resolved", "known", "ignored"}:
                raise ValueError("final mismatch status is invalid")
            rows = self.store.repository.lookup("mismatches", {"id": mismatch_id}, token)
            if not rows:
                raise UploadValidationError("mismatch is unavailable")
            current = str(rows[0]["status"])
            transitions = (to_status,) if isinstance(self.store.repository, SupabaseRepository) else {
                "new": ("assigned", "in_progress", to_status),
                "reopened": ("assigned", "in_progress", to_status),
                "assigned": ("in_progress", to_status),
                "in_progress": (to_status,),
            }.get(current, ())
            if not transitions:
                raise UploadValidationError("mismatch is already handled")
            for status in transitions:
                final_step = status == to_status
                self.store.repository.transition_mismatch(mismatch_id, status, comment if final_step else "", evidence if final_step else {}, actor[0], token)
        except HTTPError as error:
            self.send(502, ("Supabase mismatch update failed: " + str(error.code)).encode(), "text/plain")
            return
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, UploadValidationError) as error:
            self.send(400, (str(error) or "mismatch payload is invalid").encode(), "text/plain")
            return
        self.send(200, json.dumps({"status": "transitioned", "mismatch_id": mismatch_id, "to_status": to_status}).encode(), "application/json")

    def select_snapshot(self) -> None:
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        actor = self._actor()
        if actor is None:
            self.send(401, b"unauthorized", "text/plain")
            return
        if self.roles.get(token, "viewer") != "admin":
            self.send(403, b"admin role required", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length).decode("utf-8"))
            period = str(payload["reporting_period"]); source = str(payload["source_type"]); snapshot_id = str(payload["snapshot_id"])
        except (KeyError, TypeError, ValueError, UnicodeDecodeError):
            self.send(400, b"selection metadata is invalid", "text/plain")
            return
        snapshot = next((item for item in self.store.snapshots if item.id == snapshot_id and item.reporting_period == period and item.source_type == source and item.team_id == actor[1]), None)
        if snapshot is None:
            self.send(404, b"snapshot not found", "text/plain")
            return
        self.store.selections[(period, source)] = snapshot.id
        self.send(201, json.dumps({"selected": snapshot.id}, ensure_ascii=False).encode(), "application/json")


if __name__ == "__main__":
    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer(bind_address(), H).serve_forever()
