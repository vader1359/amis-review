import json
import sys
import threading
from http.client import HTTPConnection
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))
import server  # noqa: E402

FIXTURES = {
    "product": "product_fixture.xlsx", "purchase": "loading_purchase_fixture.xlsx",
    "revenue": "so_chi_tiet_revenue_fixture.xlsx", "inventory": "tong_hop_ton_kho_inventory_fixture.xlsx",
    "preorder": "pre-order_fixture.xlsx", "crm": "crm_sale_fixture.xlsx", "target": "target_fixture.xlsx",
}


def _session(port: int, role: str) -> str:
    connection = HTTPConnection("127.0.0.1", port); connection.request("GET", f"/api/local-preview-session?role={role}")
    response = connection.getresponse(); payload = json.loads(response.read()); connection.close()
    assert response.status == 200
    return payload["token"]


def _upload(port: int, token: str | None, source_type: str, filename: str, fields: dict[str, str] | None = None) -> int:
    boundary = "----preview-e2e"; content = (ROOT / "tests" / "fixtures" / filename).read_bytes()
    fields = fields or {"team_id": "team-a", "reporting_period": "2026-07", "data_as_of": "2026-07-05", "source_type": source_type}
    parts = [f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode() for key, value in fields.items()]
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n".encode() + content + b"\r\n")
    body = b"".join(parts) + f"--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    connection = HTTPConnection("127.0.0.1", port); connection.request("POST", "/api/persist", body=body, headers=headers)
    response = connection.getresponse(); response.read(); connection.close()
    return response.status


def _release(port: int, token: str) -> tuple[int, dict[str, object]]:
    connection = HTTPConnection("127.0.0.1", port); connection.request("POST", "/api/release", body=json.dumps({"reporting_period": "2026-07"}), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    response = connection.getresponse(); payload = json.loads(response.read()); connection.close()
    return response.status, payload


def test_anonymous_upload_rejects_malformed_metadata_and_preserves_history() -> None:
    store = server.PsiMemoryStore(); server.H.store = store; server.H.release_service = server.PsiReleaseService(store); server.H.actors = {}; server.H.roles = {}
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H); thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        port = httpd.server_address[1]
        assert _upload(port, None, "product", "product_fixture.xlsx", {"team_id": "team-a", "reporting_period": "bad", "data_as_of": "2026-07-05", "source_type": "product"}) == 400
        assert _upload(port, None, "product", "product_fixture.xlsx") == 201
        connection = HTTPConnection("127.0.0.1", port); connection.request("GET", "/api/dashboard"); response = connection.getresponse(); payload = json.loads(response.read()); connection.close()
        assert response.status == 200 and len(payload["history"]) == 1
        assert payload["history"][0]["checksum"]
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_local_preview_upload_release_download_is_authorized_and_immutable() -> None:
    store = server.PsiMemoryStore(); server.H.store = store; server.H.release_service = server.PsiReleaseService(store); server.H.actors = {}; server.H.roles = {}
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H); thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        port = httpd.server_address[1]; contributor = _session(port, "contributor"); admin = _session(port, "admin"); viewer = _session(port, "viewer")
        assert _upload(port, None, "product", "product_fixture.xlsx") == 201
        assert _upload(port, viewer, "product", "product_fixture.xlsx") == 201
        assert _upload(port, admin, "product", "product_fixture.xlsx") == 201
        assert all(_upload(port, contributor, source_type, filename) == 201 for source_type, filename in FIXTURES.items())
        status, first = _release(port, admin); assert status == 201 and isinstance(first["signed_url"], str)
        connection = HTTPConnection("127.0.0.1", port); connection.request("GET", str(first["signed_url"]), headers={"Authorization": f"Bearer {admin}"}); response = connection.getresponse(); content = response.read(); connection.close()
        assert response.status == 200
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True); workbook.close()
        connection = HTTPConnection("127.0.0.1", port); connection.request("GET", str(first["signed_url"]), headers={"Authorization": f"Bearer {viewer}"}); response = connection.getresponse(); response.read(); connection.close(); assert response.status == 403
        second_status, second = _release(port, admin)
        assert second_status == 201 and second["object_path"] != first["object_path"]
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)
