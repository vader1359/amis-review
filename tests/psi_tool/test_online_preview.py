"""HTTP preview exercises actual routes and rejects unsafe source packages."""

import asyncio
import io
import zipfile

import httpx
import pytest
from web import preview


def package():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(zipfile.ZipInfo("[Content_Types].xml"), "test")
        archive.writestr(zipfile.ZipInfo("xl/workbook.xml"), "test")
    return stream.getvalue()


@pytest.fixture
def client(tmp_path):
    app = preview.create_app(storage_dir=tmp_path / "saved")

    class Client:
        def request(self, method, path, **kwargs):
            async def send():
                transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 12345))
                async with httpx.AsyncClient(
                    transport=transport, base_url="http://localhost"
                ) as session:
                    return await session.request(method, path, **kwargs)

            return asyncio.run(send())

        def restart(self):
            nonlocal app
            app = preview.create_app(storage_dir=tmp_path / "saved")

        def get(self, path, **kwargs):
            return self.request("GET", path, **kwargs)

        def post(self, path, **kwargs):
            return self.request("POST", path, **kwargs)

    return Client()


def test_preview_assets_and_health(client):
    for path in ("/", "/app.js", "/styles.css", "/health"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
    assert client.get("/health").json()["publication"] is False
    assert client.get("/.env").status_code == 404


def test_cross_origin_and_missing_token_block_upload(client):
    assert client.post("/api/drafts").status_code == 403
    assert (
        client.get("/api/config", headers={"Origin": "https://evil.test"}).status_code
        == 403
    )
    assert client.get("/api/config", headers={"Host": "evil.test"}).status_code == 403


def test_missing_baseline_blocks_request(client):
    token = client.get("/api/config").json()["preview_token"]
    response = client.post(
        "/api/drafts", data={"as_of": "2026-09-03"}, headers={"X-PSI-Preview": token}
    )
    assert response.status_code == 422


def test_http_build_and_download_use_same_validated_bytes(client, monkeypatch):
    from types import SimpleNamespace

    calls = []

    def build(sources, cutoff, baseline):
        calls.append((set(sources), str(cutoff), baseline.content))
        return SimpleNamespace(
            xlsx=b"validated-draft",
            input_hash="input",
            workbook_sha256="output",
            payload={"gates": [{"check": "test", "status": "PASS"}]},
        )

    monkeypatch.setattr(preview, "build_draft", build)
    token = client.get("/api/config").json()["preview_token"]
    files = {
        key: ("source.xlsx", package()) for key in [*preview.SOURCE_LABELS, "prior_psi"]
    }
    response = client.post(
        "/api/drafts",
        data={"as_of": "2026-09-03"},
        files=files,
        headers={"X-PSI-Preview": token},
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "draft"
    assert calls == [(set(preview.SOURCE_LABELS), "2026-09-03", package())]
    assert client.get(response.json()["download_url"]).content == b"validated-draft"


def test_bad_zip_cannot_reach_engine(client, monkeypatch):
    def unexpected(*args):
        pytest.fail("invalid package reached engine")

    monkeypatch.setattr(preview, "build_draft", unexpected)
    token = client.get("/api/config").json()["preview_token"]
    files = dict.fromkeys(
        [*preview.SOURCE_LABELS, "prior_psi"], ("source.xlsx", b"PKnot-a-zip")
    )
    response = client.post(
        "/api/drafts",
        data={"as_of": "2026-09-03"},
        files=files,
        headers={"X-PSI-Preview": token},
    )
    assert response.status_code == 422


def request_headers(client):
    return {"X-PSI-Preview": client.get("/api/config").json()["preview_token"]}


def all_files():
    return {
        key: ("source.xlsx", package()) for key in [*preview.SOURCE_LABELS, "prior_psi"]
    }


def fake_build(*args):
    from types import SimpleNamespace

    return SimpleNamespace(
        xlsx=b"verified", input_hash="input", workbook_sha256="hash", payload={}
    )


def test_build_saved_selection_survives_app_restart(client, monkeypatch):
    monkeypatch.setattr(preview, "build_draft", fake_build)
    first = client.post(
        "/api/drafts",
        files=all_files(),
        data={"as_of": "2026-09-03"},
        headers=request_headers(client),
    )
    assert first.status_code == 200
    saved = first.json()["saved_sources"]
    assert set(saved) == preview.REUSABLE_ROLES
    client.restart()
    assert client.get("/api/config").json()["saved_sources"] == saved
    data = {"as_of": "2026-09-10", **{role: item["id"] for role, item in saved.items()}}
    periodic = {role: value for role, value in all_files().items() if role not in saved}
    result = client.post(
        "/api/drafts", files=periodic, data=data, headers=request_headers(client)
    )
    assert result.status_code == 200, result.text
    assert result.json()["saved_sources"] == saved


def test_failed_build_does_not_persist_uploads(client, monkeypatch):
    def fail(*args):
        raise preview.PipelineError("INDEPENDENT_VALIDATION_FAILED")

    monkeypatch.setattr(preview, "build_draft", fail)
    result = client.post(
        "/api/drafts",
        files=all_files(),
        data={"as_of": "2026-09-03"},
        headers=request_headers(client),
    )
    assert result.status_code == 422
    assert client.get("/api/config").json()["saved_sources"] == {}


def test_all_mutation_verbs_require_token(client):
    for method in ("POST", "DELETE", "PUT", "PATCH"):
        assert client.request(method, "/api/sources/purchase").status_code == 403
    assert (
        client.request(
            "DELETE", "/api/sources/purchase", headers=request_headers(client)
        ).status_code
        == 200
    )
    assert (
        client.request(
            "DELETE", "/api/sources/crm", headers=request_headers(client)
        ).status_code
        == 422
    )


def test_stale_or_wrong_role_selection_is_rejected(client, monkeypatch):
    monkeypatch.setattr(preview, "build_draft", fake_build)
    first = client.post(
        "/api/drafts",
        files=all_files(),
        data={"as_of": "2026-09-03"},
        headers=request_headers(client),
    ).json()
    saved = first["saved_sources"]
    periodic = {role: value for role, value in all_files().items() if role not in saved}
    data = {"as_of": "2026-09-10", **{role: item["id"] for role, item in saved.items()}}
    data["purchase"] = saved["target"]["id"]
    assert (
        client.post(
            "/api/drafts", files=periodic, data=data, headers=request_headers(client)
        ).status_code
        == 409
    )
    data["purchase"] = saved["purchase"]["id"]
    client.request("DELETE", "/api/sources/purchase", headers=request_headers(client))
    assert (
        client.post(
            "/api/drafts", files=periodic, data=data, headers=request_headers(client)
        ).status_code
        == 409
    )


def test_batch_classify_is_read_only_and_bounded(client, monkeypatch):
    from web import preview_classify

    calls = []

    def classify(files):
        calls.append(files)
        return [
            {
                "index": i,
                "filename": name,
                "role": "crm",
                "candidates": ["crm"],
                "reason": "schema",
            }
            for i, (name, _) in enumerate(files)
        ]

    monkeypatch.setattr(preview_classify, "classify_files", classify)
    files = [("files", (f"report-{i}.xlsx", package())) for i in range(4)]
    result = client.post(
        "/api/sources/classify", files=files, headers=request_headers(client)
    )
    assert result.status_code == 200, result.text
    assert len(result.json()["files"]) == 4 and len(calls) == 1
    assert client.get("/api/config").json()["saved_sources"] == {}
    assert client.post(
        "/api/sources/classify",
        files=files + files[:1],
        headers=request_headers(client),
    ).status_code in {400, 422}
    assert (
        client.post(
            "/api/sources/classify",
            files={"files": ("bad.xlsx", b"bad")},
            headers=request_headers(client),
        ).status_code
        == 422
    )
    assert len(calls) == 1


def test_explicit_save_validates_schema_before_persist(client, monkeypatch):
    from web import preview_classify

    def reject(*args):
        raise ValueError("SOURCE_SCHEMA_INVALID")

    monkeypatch.setattr(preview_classify, "validate_reusable", reject)
    args = {
        "files": {"file": ("source.xlsx", package())},
        "headers": request_headers(client),
    }
    assert client.post("/api/sources/purchase", **args).status_code == 422
    assert client.get("/api/config").json()["saved_sources"] == {}
    monkeypatch.setattr(preview_classify, "validate_reusable", lambda *args: None)
    result = client.post("/api/sources/purchase", **args)
    assert result.status_code == 200
    assert set(result.json()) == {"id", "filename", "sha256", "size", "stored_at"}
    assert client.post("/api/sources/crm", **args).status_code == 422


def test_saved_source_hash_failure_cannot_reach_engine(client, monkeypatch, tmp_path):
    monkeypatch.setattr(preview, "build_draft", fake_build)
    result = client.post(
        "/api/drafts",
        files=all_files(),
        data={"as_of": "2026-09-03"},
        headers=request_headers(client),
    )
    saved = result.json()["saved_sources"]
    (tmp_path / "saved" / (saved["purchase"]["sha256"] + ".xlsx")).write_bytes(
        b"changed"
    )

    def unexpected(*args):
        pytest.fail("corrupted saved file reached engine")

    monkeypatch.setattr(preview, "build_draft", unexpected)
    periodic = {role: value for role, value in all_files().items() if role not in saved}
    data = {"as_of": "2026-09-10", **{role: item["id"] for role, item in saved.items()}}
    result = client.post(
        "/api/drafts", files=periodic, data=data, headers=request_headers(client)
    )
    assert result.status_code == 409
    assert result.json()["error"] == "SAVED_SOURCE_INTEGRITY_FAILED"


def test_malformed_workbook_xml_returns_public_error(client):
    result = client.post(
        "/api/sources/target",
        files={"file": ("target.xlsx", package())},
        headers=request_headers(client),
    )
    assert result.status_code == 422
    assert result.json()["detail"] == "SOURCE_SCHEMA_INVALID"
    result = client.post(
        "/api/sources/prior_psi",
        files={"file": ("PSI_Final.xlsx", package())},
        headers=request_headers(client),
    )
    assert result.status_code == 422
    assert client.get("/api/config").json()["saved_sources"] == {}


def test_successful_draft_uploads_do_not_replace_retained_files(client, monkeypatch):
    monkeypatch.setattr(preview, "build_draft", fake_build)
    initial = client.post(
        "/api/drafts",
        files=all_files(),
        data={"as_of": "2026-09-03"},
        headers=request_headers(client),
    )
    assert initial.status_code == 200
    saved = initial.json()["saved_sources"]
    uploaded = {role: ("changed.xlsx", package() + b"changed") for role in all_files()}
    built = []

    def build(sources, cutoff, baseline):
        built.append((sources["purchase"].filename, baseline.filename))
        return fake_build()

    monkeypatch.setattr(preview, "build_draft", build)
    result = client.post(
        "/api/drafts",
        files=uploaded,
        data={"as_of": "2026-09-10"},
        headers=request_headers(client),
    )
    assert result.status_code == 200
    assert built == [("changed.xlsx", "changed.xlsx")]
    assert result.json()["saved_sources"] == saved
    assert client.get("/api/config").json()["saved_sources"] == saved
    client.restart()
    assert client.get("/api/config").json()["saved_sources"] == saved


def test_explicit_save_can_replace_retained_file(client, monkeypatch):
    from web import preview_classify

    monkeypatch.setattr(preview_classify, "validate_reusable", lambda *args: None)
    first = client.post(
        "/api/sources/target",
        files={"file": ("target.xlsx", package())},
        headers=request_headers(client),
    )
    second = client.post(
        "/api/sources/target",
        files={"file": ("new-target.xlsx", package() + b"new")},
        headers=request_headers(client),
    )
    assert first.status_code == second.status_code == 200
    assert second.json()["id"] != first.json()["id"]
    assert second.json()["sha256"] != first.json()["sha256"]
    assert client.get("/api/config").json()["saved_sources"]["target"] == second.json()
