# Copyright 2026 PSI Tool contributors
"""No-follow component walk for one lexical output parent chain."""

from __future__ import annotations

import errno
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from ._fd_types import DirectoryFd

if TYPE_CHECKING:
    from pathlib import Path

ERROR_TRAVERSAL: Final = "output directory must be traversal-free"
ERROR_WORKSPACE: Final = "workspace root must be absolute and traversal-free"
ERROR_PLATFORM: Final = "descriptor-anchored output is unsupported"
ERROR_CHAIN_CHANGED: Final = "output parent chain identity changed"

type FileIdentity = tuple[int, int]


@dataclass(frozen=True, slots=True)
class OpenedParent:
    """Retained no-follow descriptors and identities for one parent chain."""

    components: tuple[str, ...]
    descriptors: tuple[DirectoryFd, ...]
    identities: tuple[FileIdentity, ...]
    final_name: str

    @property
    def parent_fd(self) -> DirectoryFd:
        return self.descriptors[-1]


def open_parent_chain(output_dir: Path, workspace_root: Path) -> OpenedParent:
    """Walk from the stable filesystem root without reopening a full path."""
    target = _lexical_target(output_dir, workspace_root)
    components = tuple(target.parts[1:-1])
    flags = _directory_flags()
    descriptors: list[DirectoryFd] = []
    identities: list[FileIdentity] = []
    try:
        current = DirectoryFd(os.open("/", flags))
        descriptors.append(current)
        identities.append(_identity(current))
        for component in components:
            current = DirectoryFd(os.open(component, flags, dir_fd=current))
            descriptors.append(current)
            identities.append(_identity(current))
    except OSError:
        close_descriptors(tuple(descriptors))
        raise
    return OpenedParent(
        components=components,
        descriptors=tuple(descriptors),
        identities=tuple(identities),
        final_name=target.name,
    )


def verify_parent_chain(parent: OpenedParent) -> None:
    """Freshly walk the lexical chain and compare every retained inode identity."""
    flags = _directory_flags()
    current = DirectoryFd(os.open("/", flags))
    try:
        if _identity(current) != parent.identities[0]:
            raise OSError(errno.ESTALE, ERROR_CHAIN_CHANGED)
        for component, expected in zip(
            parent.components,
            parent.identities[1:],
            strict=True,
        ):
            next_fd = DirectoryFd(os.open(component, flags, dir_fd=current))
            os.close(current)
            current = next_fd
            if _identity(current) != expected:
                raise OSError(errno.ESTALE, ERROR_CHAIN_CHANGED)
    finally:
        os.close(current)


def close_descriptors(descriptors: tuple[DirectoryFd, ...]) -> None:
    for descriptor in reversed(descriptors):
        os.close(descriptor)


def directory_flags() -> int:
    """Return fail-closed flags shared by owned child directory opens."""
    return _directory_flags()


def _lexical_target(output_dir: Path, workspace_root: Path) -> Path:
    if ".." in output_dir.parts or output_dir.name in {"", ".", ".."}:
        raise OSError(errno.EINVAL, ERROR_TRAVERSAL)
    if (
        not workspace_root.is_absolute()
        or ".." in workspace_root.parts
        or workspace_root.name in {"", ".", ".."}
    ):
        raise OSError(errno.EINVAL, ERROR_WORKSPACE)
    target = output_dir if output_dir.is_absolute() else workspace_root / output_dir
    if target.anchor != "/":
        raise OSError(errno.ENOTSUP, ERROR_PLATFORM)
    return target


def _directory_flags() -> int:
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise OSError(errno.ENOTSUP, ERROR_PLATFORM)
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _identity(descriptor: DirectoryFd) -> FileIdentity:
    item = os.fstat(descriptor)
    return item.st_dev, item.st_ino
