"""Private local selection store; saved files are not approval receipts."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from psi_tool.online_pipeline import MAX_SOURCE_BYTES, SourceSnapshot

REUSABLE_ROLES = frozenset({"purchase", "target", "manual_check", "prior_psi"})
HEX_ID = re.compile(r"[a-f0-9]{32}")
HEX_SHA = re.compile(r"[a-f0-9]{64}")


class StoreError(ValueError):
    """A safe public error code, without filesystem details."""


def default_storage_dir() -> Path:
    return Path.home() / ".cache" / "amis-psi-preview" / "saved-sources"


class SourceStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.directory.is_symlink():
            raise StoreError("SOURCE_STORE_INVALID")
        os.chmod(self.directory, 0o700)
        descriptor = os.open(
            self.directory / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)

    def _read(self, path: Path, maximum: int) -> bytes:
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, "rb") as stream:
                content = stream.read(maximum + 1)
            if len(content) > maximum:
                raise StoreError("SAVED_SOURCE_INTEGRITY_FAILED")
            return content
        except OSError as exc:
            raise StoreError("SAVED_SOURCE_INTEGRITY_FAILED") from exc

    def _metadata(self) -> dict:
        path = self.directory / "active.json"
        if not path.exists() and not path.is_symlink():
            return {}
        try:
            metadata = json.loads(self._read(path, 16384))
            if not isinstance(metadata, dict) or not set(metadata) <= REUSABLE_ROLES:
                raise ValueError()
            for item in metadata.values():
                if (
                    not isinstance(item, dict)
                    or set(item) != {"id", "filename", "sha256", "size", "stored_at"}
                    or not isinstance(item["id"], str)
                    or not HEX_ID.fullmatch(item["id"])
                    or not isinstance(item["sha256"], str)
                    or not HEX_SHA.fullmatch(item["sha256"])
                    or type(item["size"]) is not int
                    or not 0 < item["size"] <= MAX_SOURCE_BYTES
                    or not isinstance(item["filename"], str)
                    or not item["filename"]
                    or len(item["filename"]) > 255
                    or "/" in item["filename"]
                    or "\\" in item["filename"]
                    or not isinstance(item["stored_at"], str)
                ):
                    raise ValueError()
                datetime.fromisoformat(item["stored_at"])
            return metadata
        except (ValueError, TypeError, KeyError) as exc:
            raise StoreError("SOURCE_STORE_INVALID") from exc

    def _atomic_write(self, target: Path, content: bytes) -> None:
        temporary = self.directory / (".tmp-" + secrets.token_hex(16))
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            directory_fd = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)

    def _commit(self, metadata: dict) -> None:
        self._atomic_write(
            self.directory / "active.json",
            json.dumps(metadata, ensure_ascii=False).encode(),
        )
        # Only four active selections are retained; obsolete snapshots cannot grow
        # the cache indefinitely and their opaque references are rejected.
        active = {item["sha256"] + ".xlsx" for item in metadata.values()}
        for path in self.directory.glob("*.xlsx"):
            if HEX_SHA.fullmatch(path.stem) and path.name not in active:
                path.unlink(missing_ok=True)

    def list(self) -> dict:
        with self._locked():
            return self._metadata()

    def save_missing(self, sources: dict[str, SourceSnapshot]) -> dict:
        """Seed absent roles without replacing a previously retained selection."""
        return self.save_many(sources, overwrite=False)

    def save_many(
        self, sources: dict[str, SourceSnapshot], *, overwrite: bool = True
    ) -> dict:
        if not set(sources) <= REUSABLE_ROLES:
            raise StoreError("SAVED_SOURCE_ROLE_INVALID")
        with self._locked():
            metadata = self._metadata()
            for role, snapshot in sources.items():
                if not overwrite and role in metadata:
                    continue
                if (
                    not 0 < len(snapshot.content) <= MAX_SOURCE_BYTES
                    or hashlib.sha256(snapshot.content).hexdigest() != snapshot.sha256
                ):
                    raise StoreError("SAVED_SOURCE_INTEGRITY_FAILED")
                filename = snapshot.filename.replace("\\", "/").rsplit("/", 1)[-1]
                if not filename or len(filename) > 255:
                    raise StoreError("SOURCE_FILENAME_INVALID")
                target = self.directory / (snapshot.sha256 + ".xlsx")
                if target.exists() or target.is_symlink():
                    if self._read(target, MAX_SOURCE_BYTES) != snapshot.content:
                        raise StoreError("SAVED_SOURCE_INTEGRITY_FAILED")
                else:
                    self._atomic_write(target, snapshot.content)
                metadata[role] = {
                    "id": secrets.token_hex(16),
                    "filename": filename,
                    "sha256": snapshot.sha256,
                    "size": len(snapshot.content),
                    "stored_at": datetime.now(timezone.utc).isoformat(),
                }
            self._commit(metadata)
            return metadata

    def resolve(self, role: str, identifier: str) -> SourceSnapshot:
        if role not in REUSABLE_ROLES:
            raise StoreError("SAVED_SOURCE_ROLE_INVALID")
        if not HEX_ID.fullmatch(identifier):
            raise StoreError("SAVED_SOURCE_NOT_FOUND")
        with self._locked():
            item = self._metadata().get(role)
            if not item or item["id"] != identifier:
                raise StoreError("SAVED_SOURCE_NOT_FOUND")
            content = self._read(
                self.directory / (item["sha256"] + ".xlsx"), MAX_SOURCE_BYTES
            )
            snapshot = SourceSnapshot.from_bytes(item["filename"], content)
            if snapshot.sha256 != item["sha256"] or len(content) != item["size"]:
                raise StoreError("SAVED_SOURCE_INTEGRITY_FAILED")
            return snapshot

    def clear(self, role: str) -> dict:
        if role not in REUSABLE_ROLES:
            raise StoreError("SAVED_SOURCE_ROLE_INVALID")
        with self._locked():
            metadata = self._metadata()
            metadata.pop(role, None)
            self._commit(metadata)
            return metadata
