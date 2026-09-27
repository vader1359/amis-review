"""Authenticated, fail-closed adapter for a single HTTPS Quick Tunnel host.

Run on loopback with uvicorn --no-proxy-headers. PSI_TUNNEL_CONFIG names a
private JSON file with username, password, and public_host. Configuration is
loaded once; restart this gateway after the Quick Tunnel hostname changes.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import time
from http.cookies import CookieError, SimpleCookie
from pathlib import Path

from starlette.responses import JSONResponse

from web.preview import create_app

SECURITY_HEADERS = {
    b"cache-control": b"no-store",
    b"x-robots-tag": b"noindex, nofollow",
    b"x-content-type-options": b"nosniff",
}


def load_config(path: str | None) -> dict[str, str] | None:
    """Return validated credentials, never include configuration in errors."""
    try:
        if not path:
            return None
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict) or set(value) != {
            "username",
            "password",
            "public_host",
        }:
            return None
        if not all(isinstance(item, str) for item in value.values()):
            return None
        username, password, host = (
            value["username"],
            value["password"],
            value["public_host"],
        )
        if (
            not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", username)
            or not 8 <= len(password) <= 256
            or not password.isascii()
            or any(ord(char) < 33 or ord(char) > 126 for char in password)
            or not re.fullmatch(
                r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com", host
            )
        ):
            return None
    except (OSError, ValueError, UnicodeError):
        return None
    return value


class TunnelGateway:
    """Gate every request before allowing the local preview app to see it."""

    def __init__(self, inner, config_path: str | None = None):
        self.inner = inner
        self.config = load_config(config_path)

    def session_signature(self, value):
        config = self.config
        message = f"{config['public_host']}:{config['username']}:{value}".encode()
        return hmac.new(
            config["password"].encode(), message, hashlib.sha256
        ).hexdigest()

    def valid_session(self, raw_cookie):
        try:
            cookies = SimpleCookie()
            cookies.load(raw_cookie.decode("ascii"))
            value = cookies["__Host-psi-session"].value
            expiry, nonce, signature = value.split(".")
            return (
                0 < int(expiry) - time.time() <= 43200
                and len(nonce) == 32
                and secrets.compare_digest(
                    signature, self.session_signature(f"{expiry}.{nonce}")
                )
            )
        except (ValueError, KeyError, UnicodeError, CookieError):
            return False

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.inner(scope, receive, send)
            return
        if scope["type"] != "http":
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            return

        async def secure_send(message):
            if message["type"] == "http.response.start":
                message = dict(message)
                message["headers"] = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() not in SECURITY_HEADERS
                ] + list(SECURITY_HEADERS.items())
            await send(message)

        async def reject(status, code, headers=None):
            await JSONResponse({"error": code}, status, headers=headers)(
                scope, receive, secure_send
            )

        config = self.config
        if config is None:
            await reject(503, "TUNNEL_NOT_CONFIGURED")
            return
        try:
            peer = scope.get("client")
            loopback = peer and ipaddress.ip_address(peer[0]).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            await reject(403, "TUNNEL_PEER_FORBIDDEN")
            return

        headers = {}
        guarded = {
            b"host",
            b"cookie",
            b"authorization",
            b"origin",
            b"sec-fetch-site",
            b"x-forwarded-proto",
        }
        for key, value in scope.get("headers", []):
            key = key.lower()
            if key in guarded and key in headers:
                await reject(403, "TUNNEL_HEADERS_INVALID")
                return
            headers[key] = value
        if (
            headers.get(b"host") != config["public_host"].encode("ascii")
            or headers.get(b"x-forwarded-proto") != b"https"
        ):
            await reject(403, "TUNNEL_ORIGIN_FORBIDDEN")
            return

        origin = headers.get(b"origin")
        # Opening the login page from an external link is a safe navigation.
        public_navigation = (
            scope["method"] in {"GET", "HEAD"}
            and scope["path"] == "/"
            and origin is None
            and headers.get(b"sec-fetch-mode") == b"navigate"
            and headers.get(b"sec-fetch-dest") == b"document"
        )
        if (
            origin is not None
            and origin != f"https://{config['public_host']}".encode("ascii")
        ) or (
            headers.get(b"sec-fetch-site", b"").lower() == b"cross-site"
            and not public_navigation
        ):
            await reject(403, "TUNNEL_ORIGIN_FORBIDDEN")
            return

        if scope["path"] == "/__login" and scope["method"] == "POST":
            if origin != f"https://{config['public_host']}".encode("ascii"):
                await reject(403, "TUNNEL_ORIGIN_FORBIDDEN")
                return
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > 4096:
                    await reject(413, "LOGIN_TOO_LARGE")
                    return
                if not message.get("more_body", False):
                    break
            try:
                data = json.loads(body)
                username, password = data["username"], data["password"]
                if not isinstance(username, str) or not isinstance(password, str):
                    raise ValueError
                user_ok = secrets.compare_digest(
                    username.encode(), config["username"].encode()
                )
                password_ok = secrets.compare_digest(
                    password.encode(), config["password"].encode()
                )
                valid = user_ok & password_ok
            except (ValueError, KeyError, TypeError):
                valid = False
            if not valid:
                await reject(401, "LOGIN_INVALID")
                return
            value = f"{int(time.time()) + 43200}.{secrets.token_hex(16)}"
            response = JSONResponse({"ok": True})
            response.set_cookie(
                "__Host-psi-session",
                value + "." + self.session_signature(value),
                max_age=43200,
                secure=True,
                httponly=True,
                samesite="strict",
                path="/",
            )
            await response(scope, receive, secure_send)
            return

        authenticated = False
        try:
            scheme, encoded = headers.get(b"authorization", b"").split(b" ", 1)
            if scheme.lower() == b"basic":
                decoded = base64.b64decode(encoded, validate=True)
                username, separator, password = decoded.partition(b":")
                user_ok = secrets.compare_digest(username, config["username"].encode())
                password_ok = secrets.compare_digest(
                    password, config["password"].encode()
                )
                authenticated = bool(separator) & user_ok & password_ok
        except (ValueError, binascii.Error):
            pass
        authenticated = authenticated or self.valid_session(headers.get(b"cookie", b""))
        public_asset = scope["method"] in {"GET", "HEAD"} and scope["path"] in {
            "/",
            "/app.js",
            "/styles.css",
        }
        if (
            not authenticated
            and scope["path"] == "/api/config"
            and scope["method"] == "GET"
        ):
            await JSONResponse(
                {"login_required": True, "style_nonce": self.inner.state.style_nonce}
            )(scope, receive, secure_send)
            return
        if not authenticated and not public_asset:
            await reject(
                401,
                "AUTHENTICATION_REQUIRED",
            )
            return

        forwarded = dict(scope)
        forwarded["scheme"] = "http"
        forwarded["server"] = ("127.0.0.1", 18788)
        forwarded["headers"] = [
            (key, value)
            for key, value in scope.get("headers", [])
            if key.lower()
            not in {b"host", b"origin", b"authorization", b"forwarded", b"cookie"}
            and not key.lower().startswith(b"x-forwarded-")
            and not (public_navigation and key.lower() == b"sec-fetch-site")
        ] + [(b"host", b"127.0.0.1")]
        if origin is not None:
            forwarded["headers"].append((b"origin", b"http://127.0.0.1"))
        await self.inner(forwarded, receive, secure_send)


source_dir = os.environ.get("PSI_SOURCE_STORE_DIR")
app = TunnelGateway(
    create_app(storage_dir=Path(source_dir) if source_dir else None),
    os.environ.get("PSI_TUNNEL_CONFIG"),
)
