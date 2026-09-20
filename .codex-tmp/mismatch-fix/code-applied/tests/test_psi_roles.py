import json
import sys
import threading
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))
import server  # noqa: E402


def _release_store() -> server.PsiMemoryStore:
    store = server.PsiMemoryStore()
    fixtures = {
        "product": "product_fixture.xlsx", "purchase": "loading_purchase_fixture.xlsx",
        "revenue": "so_chi_tiet_revenue_fixture.xlsx", "inventory": "tong_hop_ton_kho_inventory_fixture.xlsx",
        "preorder": "pre-order_fixture.xlsx", "crm": "crm_sale_fixture.xlsx", "target": "target_fixture.xlsx",
    }
    for source_type, filename in fixtures.items():
        store.persist(server.UploadRequest("team-a", "user-a", "2026-07", "2026-07-05", source_type, filename, (ROOT / "tests" / "fixtures" / filename).read_bytes()))
    return store


def _serve(store: server.PsiMemoryStore) -> tuple[server.ThreadingHTTPServer, threading.Thread]:
    server.H.store = store
    server.H.release_service = server.PsiReleaseService(store)
    server.H.actors = {"admin-token": ("user-a", "team-a"), "viewer-token": ("viewer", "team-a"), "reviewer-token": ("reviewer", "team-a")}
    server.H.roles = {"admin-token": "admin", "viewer-token": "viewer", "reviewer-token": "reviewer"}
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    return httpd, thread


def _post(port: int, payload: object, token: str = "admin-token") -> tuple[int, str, bytes]:
    connection = HTTPConnection("127.0.0.1", port)
    connection.request("POST", "/api/release", body=json.dumps(payload), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    response = connection.getresponse(); content_type = response.getheader("Content-Type", ""); body = response.read(); connection.close()
    return response.status, content_type, body


def _assert_gate_error(result: tuple[int, str, bytes], reason: str) -> None:
    status, content_type, body = result
    payload = json.loads(body)
    assert status == 400
    assert content_type == "application/json"
    assert payload["error"] == "release_gate_blocked"
    assert reason in payload["reasons"]


def test_release_rejects_legacy_approval_payload() -> None:
    httpd, thread = _serve(_release_store())
    try:
        status, content_type, body = _post(httpd.server_address[1], {"reporting_period": "2026-07", "approve": True})
        assert status == 400
        assert content_type == "application/json"
        assert json.loads(body)["error"] == "invalid_release_request"
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_release_gate_http_error_is_structured_and_side_effect_free() -> None:
    store = _release_store(); store.snapshots = [snapshot for snapshot in store.snapshots if snapshot.source_type != "target"]; baseline = {table: len(store.repository.rows(table)) for table in ("reconciliation_runs", "reconciliation_run_sources", "psi_drafts", "draft_sources", "psi_releases", "release_sources", "activity_logs")}; objects = set(store.repository.objects)
    httpd, thread = _serve(store)
    try:
        _assert_gate_error(_post(httpd.server_address[1], {"reporting_period": "2026-07"}), "selected source required: target")
        assert {table: len(store.repository.rows(table)) for table in baseline} == baseline
        assert set(store.repository.objects) == objects
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_release_http_allows_mismatch_diagnostics_for_authenticated_contributors() -> None:
    store = _release_store(); store.repository.insert("mismatches", {"id": "block", "reporting_period_id": "2026-07", "severity": "blocking", "status": "new"}); httpd, thread = _serve(store)
    try:
        assert _post(httpd.server_address[1], {"reporting_period": "2026-07"})[0] == 201
        assert _post(httpd.server_address[1], {"reporting_period": "2026-07"}, "viewer-token")[0] == 403
        assert _post(httpd.server_address[1], {"reporting_period": "2026-07"}, "reviewer-token")[0] == 403
        assert _post(httpd.server_address[1], {"reporting_period": "2026-07"}, "missing-token")[0] == 401
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_release_http_generates_from_latest_valid_weekly_snapshots() -> None:
    fixtures = {
        "product": "product_fixture.xlsx", "purchase": "loading_purchase_fixture.xlsx",
        "revenue": "so_chi_tiet_revenue_fixture.xlsx", "inventory": "tong_hop_ton_kho_inventory_fixture.xlsx",
        "preorder": "pre-order_fixture.xlsx", "crm": "crm_sale_fixture.xlsx", "target": "target_fixture.xlsx",
    }
    store = server.PsiMemoryStore()
    for source_type, filename in fixtures.items():
        store.persist(server.UploadRequest("team-a", "user-a", "2026-W29", "", source_type, filename, (ROOT / "tests" / "fixtures" / filename).read_bytes()))
    httpd, thread = _serve(store)
    try:
        status, _, body = _post(httpd.server_address[1], {"reporting_period": "2026-W29"})
        assert status == 201
        assert json.loads(body)["signed_url"]
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_release_http_malformed_payload_is_parseable_but_not_gate() -> None:
    httpd, thread = _serve(server.PsiMemoryStore())
    try:
        status, content_type, body = _post(httpd.server_address[1], {})
        payload = json.loads(body)
        assert status == 400 and content_type == "application/json"
        assert payload["error"] == "invalid_release_request"
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_local_release_download_is_authorized_immutable_and_openable() -> None:
    store = _release_store(); httpd, thread = _serve(store)
    try:
        first = _post(httpd.server_address[1], {"reporting_period": "2026-07"})
        assert first[0] == 201
        first_record = json.loads(first[2]); assert first_record["signed_url"]
        second = _post(httpd.server_address[1], {"reporting_period": "2026-07"})
        assert second[0] == 201
        second_record = json.loads(second[2]); assert second_record["object_path"] != first_record["object_path"]
        path = first_record["signed_url"]
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1]); connection.request("GET", path, headers={"Authorization": "Bearer admin-token"}); response = connection.getresponse(); content = response.read(); connection.close()
        assert response.status == 200
        from io import BytesIO
        from openpyxl import load_workbook
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True); workbook.close()
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1]); connection.request("GET", path, headers={"Authorization": "Bearer viewer-token"}); response = connection.getresponse(); response.read(); connection.close()
        assert response.status == 403
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_dashboard_preserves_terminal_mismatch_history() -> None:
    store = server.PsiMemoryStore()
    store.repository.insert("mismatches", {"id": "active", "source_type": "crm", "reporting_period_id": "2026-07", "fingerprint": "a", "severity": "blocking", "status": "new"})
    store.repository.insert("mismatches", {"id": "known", "source_type": "crm", "reporting_period_id": "2026-07", "fingerprint": "k", "severity": "warning", "status": "known"})
    store.repository.insert("mismatch_history", {"mismatch_id": "known", "from_status": "in_progress", "to_status": "known", "comment": "accepted", "evidence": {"ticket": "T-1"}})
    server.H.store = store
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H); thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1]); connection.request("GET", "/api/dashboard"); response = connection.getresponse(); payload = json.loads(response.read()); connection.close()
        assert response.status == 200
        assert {item["id"] for item in payload["mismatches"]} == {"active", "known"}
        assert payload["mismatches"][1]["history"][0]["comment"] == "accepted"
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_build_store_uses_service_role_key_for_server_persistence(monkeypatch) -> None:
    # Given: complete Supabase configuration with distinct server and browser keys.
    monkeypatch.setenv("SUPABASE_URL", "https://psi.example.test")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-secret")

    # When: the application repository is built.
    store = server.build_store()

    # Then: server persistence uses its privileged key rather than the browser key.
    assert isinstance(store.repository, server.SupabaseRepository)
    assert store.repository.key == "service-role-secret"


def test_public_config_exposes_only_supabase_browser_settings(monkeypatch) -> None:
    # Given: Supabase server and browser settings.
    monkeypatch.setenv("SUPABASE_URL", "https://psi.example.test")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-secret")
    httpd, thread = _serve(server.PsiMemoryStore())
    try:
        # When: the browser requests its public configuration.
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1])
        connection.request("GET", "/api/config")
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()

        # Then: only the URL and publishable key are returned.
        assert response.status == 200
        assert payload == {"url": "https://psi.example.test", "publishable_key": "publishable-test-key"}
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_static_handler_rejects_parent_directory_traversal() -> None:
    httpd, thread = _serve(server.PsiMemoryStore())
    try:
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1])
        connection.request("GET", "/../.env")
        response = connection.getresponse()
        response.read()
        connection.close()
        assert response.status == 404
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_server_bind_honors_explicit_lan_host_configuration(monkeypatch) -> None:
    monkeypatch.delenv("APP_HOST", raising=False)
    monkeypatch.delenv("PSI_BIND_HOST", raising=False)
    assert server.bind_address() == ("127.0.0.1", 8787)
    monkeypatch.setenv("APP_HOST", "0.0.0.0")
    assert server.bind_address() == ("0.0.0.0", 8787)
    monkeypatch.setenv("PSI_BIND_HOST", "192.168.1.20")
    assert server.bind_address() == ("192.168.1.20", 8787)


def test_local_dashboard_is_anonymous_and_empty() -> None:
    server.H.store = server.PsiMemoryStore()
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1]); connection.request("GET", "/api/dashboard"); response = connection.getresponse(); payload = json.loads(response.read()); connection.close()
        assert response.status == 200
        assert payload["history"] == []
        assert payload["matrix"] == []
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_local_admin_preview_session_authenticates_publish_action() -> None:
    server.H.store = server.PsiMemoryStore()
    server.H.release_service = server.PsiReleaseService(server.H.store)
    server.H.actors = {}
    server.H.roles = {}
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1])
        connection.request("GET", "/api/local-preview-session?role=admin")
        response = connection.getresponse(); payload = json.loads(response.read()); connection.close()
        assert response.status == 200
        assert payload["role"] == "admin"
        token = payload["token"]
        assert server.H.roles[token] == "admin"
        status, content_type, body = _post(httpd.server_address[1], {"reporting_period": "2026-07"}, token)
        assert status == 400 and content_type == "application/json"
        assert json.loads(body)["error"] == "release_gate_blocked"
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_snapshot_selection_is_admin_only_and_visible_in_dashboard() -> None:
    fixture = ROOT / "tests" / "fixtures" / "product_fixture.xlsx"
    request = server.UploadRequest(team_id="team-a", actor_id="user-a", reporting_period="2026-07", data_as_of="2026-07-05", source_type="product", filename="product_fixture.xlsx", content=fixture.read_bytes())
    store = server.PsiMemoryStore(); persisted = store.persist(request)
    server.H.store = store
    server.H.actors = {"viewer-token": ("user-a", "team-a"), "admin-token": ("admin", "team-a")}
    server.H.roles = {"viewer-token": "viewer", "admin-token": "admin"}
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H); thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        body = json.dumps({"snapshot_id": persisted.snapshot.id, "reporting_period": "2026-07", "source_type": "product"}).encode()
        for token, expected in (("viewer-token", 403), ("admin-token", 201)):
            connection = HTTPConnection("127.0.0.1", httpd.server_address[1]); connection.request("POST", "/api/select", body=body, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}); response = connection.getresponse(); response.read(); connection.close(); assert response.status == expected
        connection = HTTPConnection("127.0.0.1", httpd.server_address[1]); connection.request("GET", "/api/dashboard", headers={"Authorization": "Bearer viewer-token"}); response = connection.getresponse(); payload = json.loads(response.read()); connection.close()
        assert payload["history"][0]["selected"] is True
        assert payload["matrix"][0]["selected"] is True
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)
