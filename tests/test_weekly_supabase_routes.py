import sys
import threading
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))
import server  # noqa: E402


class _Persisted:
    def to_json(self) -> dict[str, str]:
        return {"status": "persisted"}


def test_supabase_upload_uses_bearer_identity_without_local_role_cache(monkeypatch) -> None:
    # Given: a Supabase-backed store and a caller bearer unknown to local process state.
    repository = server.SupabaseRepository("https://psi.example.test", "publishable-key")
    store = server.PsiMemoryStore(repository)
    observed: dict[str, str] = {}
    monkeypatch.setattr(repository, "authenticated_actor", lambda token: "actor-from-bearer")

    def persist(request: server.UploadRequest, auth_token: str) -> _Persisted:
        observed["actor"] = request.actor_id
        observed["token"] = auth_token
        return _Persisted()

    monkeypatch.setattr(store, "persist", persist)
    server.H.store = store
    server.H.actors = {}
    server.H.roles = {}
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    body = b"--psi\r\nContent-Disposition: form-data; name=\"team_id\"\r\n\r\nteam-a\r\n--psi\r\nContent-Disposition: form-data; name=\"week\"\r\n\r\n2026-W29\r\n--psi\r\nContent-Disposition: form-data; name=\"source_type\"\r\n\r\nproduct\r\n--psi\r\nContent-Disposition: form-data; name=\"file\"; filename=\"product_fixture.xlsx\"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\nfixture\r\n--psi--\r\n"
    try:
        # When: the browser uploads with an authenticated bearer.
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1])
        connection.request("POST", "/api/weekly-upload", body=body, headers={"Authorization": "Bearer external-session", "Content-Type": "multipart/form-data; boundary=psi", "Content-Length": str(len(body))})
        response = connection.getresponse()
        response.read()
        connection.close()

        # Then: Supabase identity is forwarded without local actor/role lookup.
        assert response.status == 201
        assert observed == {"actor": "actor-from-bearer", "token": "external-session"}
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
