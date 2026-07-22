import json
import sys
import threading
from http.client import HTTPConnection
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))
import server  # noqa: E402
import weekly_routes  # noqa: E402


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


def test_supabase_upload_returns_controlled_error_when_server_role_is_denied(monkeypatch) -> None:
    # Given: an authenticated Supabase caller whose server-side persistence is denied upstream.
    repository = server.SupabaseRepository("https://psi.example.test", "service-role-key")
    store = server.PsiMemoryStore(repository)
    monkeypatch.setattr(repository, "authenticated_actor", lambda token: "actor-from-bearer")

    def persist(_request: server.UploadRequest, auth_token: str) -> _Persisted:
        raise HTTPError("https://psi.example.test/rest/v1/profiles", 403, "Forbidden", {}, BytesIO(b'{"message":"permission denied"}'))

    monkeypatch.setattr(store, "persist", persist)
    server.H.store = store
    server.H.actors = {}
    server.H.roles = {}
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    body = b"--psi\r\nContent-Disposition: form-data; name=\"team_id\"\r\n\r\nteam-a\r\n--psi\r\nContent-Disposition: form-data; name=\"week\"\r\n\r\n2026-W29\r\n--psi\r\nContent-Disposition: form-data; name=\"source_type\"\r\n\r\nproduct\r\n--psi\r\nContent-Disposition: form-data; name=\"file\"; filename=\"product_fixture.xlsx\"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\nfixture\r\n--psi--\r\n"
    try:
        # When: upstream persistence rejects the upload.
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1])
        connection.request("POST", "/api/weekly-upload", body=body, headers={"Authorization": "Bearer external-session", "Content-Type": "multipart/form-data; boundary=psi", "Content-Length": str(len(body))})
        response = connection.getresponse()
        payload = response.read()
        connection.close()

        # Then: the browser receives an authorization response instead of a dropped connection.
        assert response.status == 403
        assert payload == b"Supabase persistence is not authorized"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_staged_upload_downloads_persists_and_cleans_up(monkeypatch) -> None:
    repository = server.SupabaseRepository("https://psi.example.test", "service-role-key")
    store = server.PsiMemoryStore(repository)
    observed: dict[str, object] = {}
    monkeypatch.setattr(repository, "authenticated_actor", lambda token: "actor-from-bearer")
    monkeypatch.setattr(
        repository,
        "lookup",
        lambda table, filters, token="": [{"team_id": "team-a"}] if table == "team_memberships" else [],
    )
    monkeypatch.setattr(
        weekly_routes,
        "storage_download",
        lambda repo, bucket, path, token: observed.update(download=(bucket, path, token)) or b"fixture",
    )
    monkeypatch.setattr(
        weekly_routes,
        "storage_delete",
        lambda repo, bucket, path, token: observed.update(delete=(bucket, path, token)),
    )

    def persist(request: server.UploadRequest, auth_token: str) -> _Persisted:
        observed["request"] = request
        observed["auth_token"] = auth_token
        return _Persisted()

    monkeypatch.setattr(store, "persist", persist)
    monkeypatch.setattr(server.H, "store", store)
    path = "team-a/staging/11111111-1111-4111-8111-111111111111.xlsx"
    payload = json.dumps({
        "team_id": "team-a",
        "week": "2026-07",
        "data_as_of": "2026-07-09",
        "source_type": "product",
        "filename": "product_fixture.xlsx",
        "staging_path": path,
    }).encode()
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1])
        connection.request(
            "POST",
            "/api/weekly_upload_staged",
            body=payload,
            headers={"Authorization": "Bearer external-session", "Content-Type": "application/json"},
        )
        response = connection.getresponse()
        response.read()
        connection.close()

        assert response.status == 201
        request = observed["request"]
        assert isinstance(request, server.UploadRequest)
        assert request.actor_id == "actor-from-bearer"
        assert request.filename == "product_fixture.xlsx"
        assert request.content == b"fixture"
        assert observed["download"] == ("psi-source", path, "external-session")
        assert observed["delete"] == ("psi-source", path, "external-session")
        assert observed["auth_token"] == "external-session"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_staged_upload_rejects_path_outside_authenticated_team(monkeypatch) -> None:
    repository = server.SupabaseRepository("https://psi.example.test", "service-role-key")
    store = server.PsiMemoryStore(repository)
    monkeypatch.setattr(repository, "authenticated_actor", lambda token: "actor-from-bearer")
    monkeypatch.setattr(
        repository,
        "lookup",
        lambda table, filters, token="": [{"team_id": "team-a"}] if table == "team_memberships" else [],
    )
    monkeypatch.setattr(
        weekly_routes,
        "storage_download",
        lambda *args: (_ for _ in ()).throw(AssertionError("invalid staging path must not be downloaded")),
    )
    monkeypatch.setattr(server.H, "store", store)
    payload = json.dumps({
        "team_id": "team-a",
        "week": "2026-07",
        "data_as_of": "2026-07-09",
        "source_type": "product",
        "filename": "product_fixture.xlsx",
        "staging_path": "other-team/staging/11111111-1111-4111-8111-111111111111.xlsx",
    }).encode()
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1])
        connection.request(
            "POST",
            "/api/weekly_upload_staged",
            body=payload,
            headers={"Authorization": "Bearer external-session", "Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = response.read()
        connection.close()

        assert response.status == 400
        assert body == b"staging_path is invalid"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
