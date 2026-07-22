import io
import json
import sys
import threading
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))
import server  # noqa: E402


def test_supabase_transport_maps_uuid_lookups_and_storage() -> None:
    from http.server import BaseHTTPRequestHandler

    requests: list[tuple[str, str, str, bytes]] = []

    class Recorder(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append((self.command, self.path, self.headers["Authorization"] or "", b""))
            payload = b'[{"id":"period-uuid","team_id":"team-uuid","profile_id":"actor-uuid","version":3,"status":"resolved","fingerprint":"fp"}]'
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

        def do_POST(self) -> None:
            content = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            requests.append((self.command, self.path, self.headers["Authorization"] or "", content))
            self.send_response(201); self.send_header("Content-Length", "0"); self.end_headers()

        def log_message(self, *_args: str) -> None:
            return

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        repository = server.SupabaseRepository(f"http://127.0.0.1:{httpd.server_address[1]}", "test-only-secret")
        assert repository.lookup("reporting_periods", {"period_key": "2026-07"}, "user-token")[0]["id"] == "period-uuid"
        repository.upload("team-uuid/2026-07/product/v1-file.xlsx", b"xlsx", "user-token")
        repository.insert("source_snapshots", {"id": "snapshot-uuid", "team_id": "team-uuid", "reporting_period_id": "period-uuid"}, "user-token")
        assert requests[0][1] == "/rest/v1/reporting_periods?period_key=eq.2026-07"
        assert requests[0][2] == "Bearer test-only-secret"
        assert requests[1][1] == "/storage/v1/object/psi-source/team-uuid/2026-07/product/v1-file.xlsx"
        assert requests[1][2] == "Bearer test-only-secret"
        assert json.loads(requests[2][3])["reporting_period_id"] == "period-uuid"
        assert requests[2][2] == "Bearer test-only-secret"
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_supabase_persistence_uses_authenticated_identity_staged_object_and_upsert() -> None:
    requests: list[tuple[str, str, str, bytes]] = []

    class Recorder(server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append((self.command, self.path, self.headers["Authorization"] or "", b""))
            payload = b'[]'
            if self.path.startswith("/auth/v1/user"):
                payload = b'{"id":"actor-uuid"}'
            elif "profiles" in self.path:
                payload = b'[{"id":"actor-uuid"}]'
            elif "team_memberships" in self.path:
                payload = b'[{"team_id":"team-uuid","profile_id":"actor-uuid","role":"contributor"}]'
            elif "reporting_periods" in self.path:
                payload = b'[{"id":"period-uuid","period_key":"2026-07"}]'
            elif "rule_versions" in self.path:
                payload = b'[{"id":"rule-uuid","version":1}]'
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

        def do_POST(self) -> None:
            content = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            requests.append((self.command, self.path, self.headers["Authorization"] or "", content)); self.send_response(201); self.send_header("Content-Length", "0"); self.end_headers()

        def log_message(self, *_args: str) -> None:
            return

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder); thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        repository = server.SupabaseRepository(f"http://127.0.0.1:{httpd.server_address[1]}", "test-only-secret")
        store = server.PsiMemoryStore(repository=repository)
        workbook = Workbook(); workbook.active.append(["unexpected"]); content = io.BytesIO(); workbook.save(content)
        request = server.UploadRequest("team-uuid", "actor-uuid", "2026-07", "2026-07-05", "product", "product_fixture.xlsx", content.getvalue())
        persisted = store.persist(request, auth_token="bearer-token")
        paths = [path for _, path, _, _ in requests]
        auth_requests = [auth for _, path, auth, _ in requests if path.startswith("/auth/v1/user")]
        persistence_requests = [auth for _, path, auth, _ in requests if not path.startswith("/auth/v1/user")]
        assert auth_requests == ["Bearer bearer-token"]
        assert all(auth == "Bearer test-only-secret" for auth in persistence_requests)
        snapshot = next(json.loads(body) for method, path, _, body in requests if method == "POST" and path == "/rest/v1/source_snapshots")
        assert paths.index("/rest/v1/upload_batches") < paths.index("/rest/v1/source_snapshots") < paths.index("/storage/v1/object/psi-source/team-uuid/" + snapshot["upload_batch_id"] + "/" + persisted.snapshot.id)
        assert "/auth/v1/user" in paths
        assert snapshot["object_path"] == f"team-uuid/{snapshot['upload_batch_id']}/{persisted.snapshot.id}"
        metadata = next(json.loads(body) for method, path, _, body in requests if method == "POST" and path == "/rest/v1/source_snapshot_metadata")
        assert metadata == {"source_snapshot_id": persisted.snapshot.id, "header_preview": ["unexpected"], "schema_gaps": [list(gap) for gap in persisted.snapshot.schema_gaps]}
        assert any(path == "/rest/v1/source_selections?on_conflict=reporting_period_id,source_type" for _, path, _, _ in requests)
        assert any(path == "/rest/v1/mismatches" and json.loads(body)["rule_version_id"] == "rule-uuid" for _, path, _, body in requests)
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_memory_transition_matches_rpc_contract() -> None:
    repository = server.PsiMemoryRepository()
    repository.insert("mismatches", {"id": "mismatch-uuid", "status": "resolved"})
    repository.transition_mismatch("mismatch-uuid", "reopened", "recurrence", {"recurrence": "true"}, "actor-uuid")
    mismatch = repository.lookup("mismatches", {"id": "mismatch-uuid"})[0]
    assert mismatch["status"] == "reopened"
    history = repository.lookup("mismatch_history", {"mismatch_id": "mismatch-uuid"})
    assert history[0]["to_status"] == "reopened"


def test_persisted_snapshot_metadata_is_written_as_json() -> None:
    repository = server.PsiMemoryRepository(); store = server.PsiMemoryStore(repository=repository)
    workbook = Workbook(); workbook.active.append(["id", "amount"]); workbook.active.append(["a", 1]); content = io.BytesIO(); workbook.save(content)
    persisted = store.persist(server.UploadRequest("team-a", "user-a", "2026-07", "2026-07-05", "product", "product_fixture.xlsx", content.getvalue()))
    row = repository.lookup("source_snapshot_metadata", {"source_snapshot_id": persisted.snapshot.id})[0]
    assert row["header_preview"] == ["id", "amount"]
    assert row["schema_gaps"] == [list(gap) for gap in persisted.snapshot.schema_gaps]


def test_supabase_mutations_use_server_role_bearer_token() -> None:
    headers: list[str] = []

    class Recorder(server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            headers.append(self.headers["Authorization"] or "")
            self.send_response(201); self.send_header("Content-Length", "0"); self.end_headers()

        def log_message(self, *_args: str) -> None:
            return

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder); thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        repository = server.SupabaseRepository(f"http://127.0.0.1:{httpd.server_address[1]}", "server-secret")
        repository.insert("upload_batches", {"id": "batch"}, "user-token"); repository.upsert("source_selections", {"id": "selection"}, "id", "user-token"); repository.upload("team/batch/snapshot", b"xlsx", "user-token"); repository.transition_mismatch("mismatch", "reopened", "recurrence", {"recurrence": "true"}, "actor", "user-token")
        assert headers == ["Bearer server-secret"] * 4
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_supabase_operations_use_service_role_without_user_bearer() -> None:
    requests: list[str] = []

    class Recorder(server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"[]")

        def do_POST(self) -> None:
            requests.append(self.path)
            self.send_response(201); self.send_header("Content-Length", "0"); self.end_headers()

        def log_message(self, *_args: str) -> None:
            return

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder); thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        repository = server.SupabaseRepository(f"http://127.0.0.1:{httpd.server_address[1]}", "server-secret")
        operations = (
            lambda: repository.lookup("profiles", {"id": "actor"}),
            lambda: repository.insert("upload_batches", {"id": "batch"}),
            lambda: repository.upsert("source_selections", {"id": "selection"}, "id"),
            lambda: repository.upload("team/batch/snapshot", b"xlsx"),
            lambda: repository.transition_mismatch("mismatch", "reopened", "recurrence", {"recurrence": "true"}, "actor"),
        )
        for operation in operations:
            operation()
        assert requests == [
            "/rest/v1/profiles?id=eq.actor",
            "/rest/v1/upload_batches",
            "/rest/v1/source_selections?on_conflict=id",
            "/storage/v1/object/psi-source/team/batch/snapshot",
            "/rest/v1/rpc/transition_mismatch",
        ]
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_authenticated_actor_rejects_whitespace_bearer_before_transport() -> None:
    requests: list[str] = []

    class Recorder(server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"{}")

        def log_message(self, *_args: str) -> None:
            return

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder); thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        repository = server.SupabaseRepository(f"http://127.0.0.1:{httpd.server_address[1]}", "server-secret")
        try:
            repository.authenticated_actor("   ")
        except server.UploadAuthorizationError:
            pass
        else:
            raise AssertionError("whitespace bearer was accepted")
        assert requests == []
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)
