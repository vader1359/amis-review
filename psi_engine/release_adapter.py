from __future__ import annotations

import json
from typing import Protocol
from urllib.request import Request, urlopen

from .persistence import UploadAuthorizationError, UploadValidationError


class ReleaseStorage(Protocol):
    url: str
    key: str


def storage_upload(repository: ReleaseStorage, bucket: str, path: str, content: bytes, token: str) -> None:
    bearer = token.strip()
    if not bearer:
        raise UploadAuthorizationError("authenticated bearer is required")
    request = Request(f"{repository.url}/storage/v1/object/{bucket}/{path}", data=content, method="POST", headers={"apikey": repository.key, "Authorization": f"Bearer {bearer}", "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"})
    with urlopen(request, timeout=10):
        pass


def storage_delete(repository: ReleaseStorage, bucket: str, path: str, token: str) -> None:
    bearer = token.strip()
    if not bearer:
        raise UploadAuthorizationError("authenticated bearer is required")
    request = Request(f"{repository.url}/storage/v1/object/{bucket}/{path}", method="DELETE", headers={"apikey": repository.key, "Authorization": f"Bearer {bearer}"})
    with urlopen(request, timeout=10):
        pass


def storage_download(repository: ReleaseStorage, bucket: str, path: str, token: str) -> bytes:
    bearer = token.strip()
    if not bearer:
        raise UploadAuthorizationError("authenticated bearer is required")
    request = Request(f"{repository.url}/storage/v1/object/{bucket}/{path}", method="GET", headers={"apikey": repository.key, "Authorization": f"Bearer {bearer}"})
    with urlopen(request, timeout=10) as response:
        return response.read()


def storage_signed_download(repository: ReleaseStorage, bucket: str, path: str, expires: int, token: str) -> str:
    bearer = token.strip()
    if not bearer:
        raise UploadAuthorizationError("authenticated bearer is required")
    request = Request(f"{repository.url}/storage/v1/object/sign/{bucket}/{path}", data=json.dumps({"expiresIn": expires}).encode(), method="POST", headers={"apikey": repository.key, "Authorization": f"Bearer {bearer}", "Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("signedURL"), str):
        raise UploadValidationError("Supabase signed URL response is invalid")
    return payload["signedURL"]
