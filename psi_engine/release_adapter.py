from __future__ import annotations

import json
from typing import Protocol
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .persistence import UploadAuthorizationError, UploadValidationError


class ReleaseStorage(Protocol):
    url: str
    key: str


def storage_upload(repository: ReleaseStorage, bucket: str, path: str, content: bytes, token: str) -> None:
    bearer = repository.key
    if not bearer:
        raise UploadAuthorizationError("authenticated bearer is required")
    object_path = quote(f"{bucket}/{path}", safe="/")
    request = Request(f"{repository.url}/storage/v1/object/{object_path}", data=content, method="POST", headers={"apikey": repository.key, "Authorization": f"Bearer {bearer}", "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"})
    with urlopen(request, timeout=300):
        pass


def storage_delete(repository: ReleaseStorage, bucket: str, path: str, token: str) -> None:
    bearer = repository.key
    if not bearer:
        raise UploadAuthorizationError("authenticated bearer is required")
    object_path = quote(f"{bucket}/{path}", safe="/")
    request = Request(f"{repository.url}/storage/v1/object/{object_path}", method="DELETE", headers={"apikey": repository.key, "Authorization": f"Bearer {bearer}"})
    with urlopen(request, timeout=10):
        pass


def storage_download(repository: ReleaseStorage, bucket: str, path: str, token: str) -> bytes:
    bearer = repository.key
    if not bearer:
        raise UploadAuthorizationError("authenticated bearer is required")
    object_path = quote(f"{bucket}/{path}", safe="/")
    request = Request(f"{repository.url}/storage/v1/object/{object_path}", method="GET", headers={"apikey": repository.key, "Authorization": f"Bearer {bearer}"})
    with urlopen(request, timeout=300) as response:
        return response.read()


def storage_signed_download(repository: ReleaseStorage, bucket: str, path: str, expires: int, token: str) -> str:
    bearer = repository.key
    if not bearer:
        raise UploadAuthorizationError("authenticated bearer is required")
    object_path = quote(f"{bucket}/{path}", safe="/")
    request = Request(f"{repository.url}/storage/v1/object/sign/{object_path}", data=json.dumps({"expiresIn": expires}).encode(), method="POST", headers={"apikey": repository.key, "Authorization": f"Bearer {bearer}", "Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("signedURL"), str):
        raise UploadValidationError("Supabase signed URL response is invalid")
    signed_url = payload["signedURL"]
    if signed_url.startswith(("http://", "https://")):
        absolute_url = signed_url
    elif signed_url.startswith("/storage/v1/"):
        absolute_url = repository.url + signed_url
    elif signed_url.startswith("/"):
        absolute_url = repository.url + "/storage/v1" + signed_url
    else:
        absolute_url = repository.url + "/storage/v1/" + signed_url
    parts = urlsplit(absolute_url)
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%"), parts.query, parts.fragment))
