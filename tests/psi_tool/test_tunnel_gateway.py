"""The public tunnel must not expose unauthenticated preview data or mutations."""

import base64
import json

import httpx
import pytest
from fastapi import FastAPI, Request
from web.preview import create_app
from web.tunnel_gateway import TunnelGateway

HOST = "psi-test-unit.trycloudflare.com"
PASSWORD = "unit-test-password-with-32-characters"
AUTH = "Basic " + base64.b64encode(f"psi:{PASSWORD}".encode()).decode()


@pytest.fixture
def config_path(tmp_path):
    path = tmp_path / "tunnel.json"
    path.write_text(
        json.dumps({"username": "psi", "password": PASSWORD, "public_host": HOST})
    )
    return str(path)


def client_for(app, peer="127.0.0.1"):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=(peer, 1234)),
        base_url=f"https://{HOST}",
        headers={"x-forwarded-proto": "https", "authorization": AUTH},
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/reports",
        "/api/drafts/private/download",
    ],
)
def test_every_path_needs_auth(config_path, path):
    import asyncio

    async def run():
        async def forbidden_inner(*args):
            pytest.fail("Unauthenticated request reached application")

        async with client_for(TunnelGateway(forbidden_inner, config_path)) as client:
            for auth in [
                "",
                "Bearer abc",
                "Basic !!!!",
                "Basic eA==",
                "Basic " + base64.b64encode(b"psi:wrong").decode(),
            ]:
                response = await client.get(path, headers={"authorization": auth})
                assert response.status_code == 401
                assert "www-authenticate" not in response.headers
                assert response.headers["cache-control"] == "no-store"
                assert response.headers["x-robots-tag"] == "noindex, nofollow"
                assert response.headers["x-content-type-options"] == "nosniff"

    asyncio.run(run())


@pytest.mark.parametrize(
    "changes",
    [
        {"host": "evil.example"},
        {"host": HOST + ":443"},
        {"x-forwarded-proto": "http"},
        {"x-forwarded-proto": "https,http"},
        {"origin": "https://evil.example"},
        {"origin": "null"},
        {"origin": f"https://{HOST}/"},
        {"sec-fetch-site": "cross-site"},
    ],
)
def test_origin_and_transport_attacks(config_path, changes):
    import asyncio

    async def run():
        async def forbidden_inner(*args):
            pytest.fail("Forbidden request reached application")

        async with client_for(TunnelGateway(forbidden_inner, config_path)) as client:
            response = await client.get("/", headers=changes)
            assert response.status_code == 403

    asyncio.run(run())


def test_peer_and_duplicate_headers(config_path):
    import asyncio

    async def run():
        async def forbidden_inner(*args):
            pytest.fail("Spoofed request reached application")

        gateway = TunnelGateway(forbidden_inner, config_path)
        async with client_for(gateway, "192.0.2.1") as client:
            response = await client.get("/", headers={"x-forwarded-for": "127.0.0.1"})
            assert response.status_code == 403
        async with client_for(gateway) as client:
            response = await client.get("/", headers=[("host", HOST), ("host", HOST)])
            assert response.status_code == 403

    asyncio.run(run())


@pytest.mark.parametrize(
    "value",
    [
        None,
        "not-json",
        "[]",
        "{}",
        json.dumps({"username": "psi", "password": "brief", "public_host": HOST}),
        json.dumps(
            {"username": "psi", "password": PASSWORD, "public_host": "evil.example"}
        ),
        json.dumps(
            {"username": "psi", "password": PASSWORD, "public_host": HOST + "/"}
        ),
    ],
)
def test_bad_configuration_fails_closed(tmp_path, value):
    import asyncio

    async def run():
        path = tmp_path / "config.json"
        if value is not None:
            path.write_text(value)

        async def forbidden_inner(*args):
            pytest.fail("Unconfigured gateway reached application")

        async with client_for(TunnelGateway(forbidden_inner, str(path))) as client:
            response = await client.get("/api/config")
            assert response.status_code == 503
            assert response.json() == {"error": "TUNNEL_NOT_CONFIGURED"}
            assert PASSWORD not in response.text
            assert response.headers["cache-control"] == "no-store"

    asyncio.run(run())


def test_real_preview_csrf_workflow(config_path, tmp_path, monkeypatch):
    import asyncio

    monkeypatch.delenv("PSI_REPORT_DATABASE_URL", raising=False)

    async def run():
        gateway = TunnelGateway(
            create_app(storage_dir=tmp_path / "sources"), config_path
        )
        async with client_for(gateway) as client:
            config = await client.get("/api/config")
            assert config.status_code == 200
            token = config.json()["preview_token"]
            response = await client.delete("/api/sources/target")
            assert response.status_code == 403
            response = await client.delete(
                "/api/sources/target",
                headers={
                    "origin": f"https://{HOST}",
                    "x-psi-preview": token,
                    "sec-fetch-site": "same-origin",
                },
            )
            assert response.status_code == 200
            assert response.json() == {"saved_sources": {}}
            assert response.headers["cache-control"] == "no-store"

    asyncio.run(run())


def test_multipart_stream_and_forwarded_headers(config_path):
    import asyncio

    async def run():
        app = FastAPI()
        body = b"--boundary\r\nContent-Disposition: form-data; name=files; filename=x.xlsx\r\n\r\n\x00binary\xff\r\n--boundary--\r\n"

        @app.post("/upload")
        async def upload(request: Request):
            assert await request.body() == body
            assert (
                request.headers["content-type"]
                == "multipart/form-data; boundary=boundary"
            )
            assert request.headers["host"] == "127.0.0.1"
            assert request.headers["origin"] == "http://127.0.0.1"
            assert request.headers["x-psi-preview"] == "preserved"
            assert "authorization" not in request.headers
            assert "x-forwarded-for" not in request.headers
            assert "forwarded" not in request.headers
            return {"ok": True}

        async with client_for(TunnelGateway(app, config_path)) as client:
            response = await client.post(
                "/upload",
                content=body,
                headers={
                    "content-type": "multipart/form-data; boundary=boundary",
                    "origin": f"https://{HOST}",
                    "x-psi-preview": "preserved",
                    "x-forwarded-for": "192.0.2.1",
                    "forwarded": "for=192.0.2.1",
                },
            )
            assert response.status_code == 200

    asyncio.run(run())


def test_browser_login_session_and_private_data(config_path, tmp_path, monkeypatch):
    import asyncio

    monkeypatch.delenv("PSI_REPORT_DATABASE_URL", raising=False)

    async def run():
        gateway = TunnelGateway(
            create_app(storage_dir=tmp_path / "sources"), config_path
        )
        async with client_for(gateway) as client:
            client.headers.pop("authorization")
            assert (await client.get("/")).status_code == 200
            config = (await client.get("/api/config")).json()
            assert set(config) == {"login_required", "style_nonce"}
            assert config["login_required"] is True
            assert (await client.get("/api/reports")).status_code == 401
            data = {"username": "psi", "password": PASSWORD}
            assert (await client.post("/__login", json=data)).status_code == 403
            headers = {"origin": f"https://{HOST}"}
            bad = await client.post(
                "/__login", json={**data, "password": "wrong"}, headers=headers
            )
            assert bad.status_code == 401 and "set-cookie" not in bad.headers
            oversized = await client.post(
                "/__login", content=b"x" * 4097, headers=headers
            )
            assert oversized.status_code == 413
            good = await client.post("/__login", json=data, headers=headers)
            assert good.status_code == 200
            cookie = good.headers["set-cookie"]
            for flag in [
                "HttpOnly",
                "Secure",
                "SameSite=strict",
                "Path=/",
                "Max-Age=43200",
            ]:
                assert flag in cookie
            config = (await client.get("/api/config")).json()
            assert "preview_token" in config and "login_required" not in config
            assert (await client.get("/api/reports")).status_code == 200
            # Cookie authentication retains the preview's existing CSRF gate.
            assert (
                await client.delete("/api/sources/target", headers=headers)
            ).status_code == 403
            assert (
                await client.delete(
                    "/api/sources/target",
                    headers={**headers, "x-psi-preview": config["preview_token"]},
                )
            ).status_code == 200
            token = client.cookies.get("__Host-psi-session")
            client.cookies.clear()
            tampered = await client.get(
                "/api/reports",
                headers={
                    "cookie": "__Host-psi-session="
                    + token[:-1]
                    + ("a" if token[-1] != "a" else "b")
                },
            )
            assert tampered.status_code == 401
            monkeypatch.setattr("web.tunnel_gateway.time.time", lambda: 9999999999)
            expired = await client.get(
                "/api/reports", headers={"cookie": "__Host-psi-session=" + token}
            )
            assert expired.status_code == 401

    asyncio.run(run())


@pytest.mark.parametrize("method,path,mode,dest,status", [
    ("GET", "/", "navigate", "document", 200),
    ("HEAD", "/", "navigate", "document", 200),
    ("POST", "/", "navigate", "document", 403),
    ("GET", "/api/reports", "navigate", "document", 403),
    ("GET", "/", "cors", "empty", 403),
    ("GET", "/", "navigate", "iframe", 403),
])
def test_external_link_only_allows_public_page_navigation(config_path, method, path, mode, dest, status):
    import asyncio
    from starlette.responses import Response

    async def run():
        async def inner(scope, receive, send):
            assert b"sec-fetch-site" not in dict(scope["headers"])
            await Response("login")(scope, receive, send)

        async with client_for(TunnelGateway(inner, config_path)) as client:
            response = await client.request(method, path, headers={
                "authorization": "", "sec-fetch-site": "cross-site",
                "sec-fetch-mode": mode, "sec-fetch-dest": dest,
            })
            assert response.status_code == status
    asyncio.run(run())
