# Copyright 2026 PSI Tool contributors
"""Descriptor-anchored lifecycle for one inspect output tree."""

from __future__ import annotations

import os
import secrets
import stat
from typing import TYPE_CHECKING, ClassVar, Final, final, override

from ._exclusive_rename import rename_exclusive
from ._fd_cleanup import remove_owned_tree
from ._fd_types import DirectoryFd
from ._fd_walk import (
    OpenedParent,
    close_descriptors,
    directory_flags,
    open_parent_chain,
    verify_parent_chain,
)

if TYPE_CHECKING:
    from pathlib import Path

ERROR_STAGE_IDENTITY: Final = "private output staging identity changed"
ERROR_STAGE_ALLOCATE: Final = "unable to allocate private output staging"
ERROR_FOREIGN: Final = "output directory is incomplete or foreign"
ERROR_UNSAFE: Final = "output directory contains unsafe state"


@final
class OutputLifecycleError(ValueError):
    """Safe public failure for an unsafe output filesystem state."""

    __slots__: ClassVar[tuple[str, ...]] = ("detail",)
    detail: str

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)

    @override
    def __str__(self) -> str:
        return self.detail


@final
class OutputSession:
    """Own the retained parent chain, output root, and cold output inode."""

    __slots__ = (
        "_closed",
        "_owned_name",
        "_parent",
        "_root_fd",
        "_root_identity",
        "is_warm",
    )

    def __init__(
        self,
        parent: OpenedParent,
        root_fd: DirectoryFd,
        owned_name: str | None,
    ) -> None:
        self._parent = parent
        self._root_fd = root_fd
        root_stat = os.fstat(root_fd)
        self._root_identity = (root_stat.st_dev, root_stat.st_ino)
        self._owned_name = owned_name
        self.is_warm = owned_name is None
        self._closed = False

    @property
    def root_fd(self) -> DirectoryFd:
        """Return the output-root descriptor without transferring ownership."""
        return self._root_fd

    def invalidate_warm_report(self) -> None:
        """Make a prior PASS unavailable before warm validation starts."""
        if self.is_warm:
            try:
                os.unlink("inspect-report.json", dir_fd=self._root_fd)
            except FileNotFoundError:
                return

    def verify_warm_identity(self) -> None:
        """Require the lexical chain and final name to retain their identities."""
        if not self.is_warm:
            return
        verify_parent_chain(self._parent)
        current = os.stat(
            self._parent.final_name,
            dir_fd=self._parent.parent_fd,
            follow_symlinks=False,
        )
        if (current.st_dev, current.st_ino) != self._root_identity:
            raise OutputLifecycleError(ERROR_STAGE_IDENTITY)

    def publish_cold(self) -> None:
        """Publish exclusively only while the full lexical chain is unchanged."""
        if self.is_warm or self._owned_name is None:
            return
        verify_parent_chain(self._parent)
        owned = os.stat(
            self._owned_name,
            dir_fd=self._parent.parent_fd,
            follow_symlinks=False,
        )
        if (owned.st_dev, owned.st_ino) != self._root_identity:
            raise OutputLifecycleError(ERROR_STAGE_IDENTITY)
        rename_exclusive(
            self._parent.parent_fd,
            self._owned_name,
            self._parent.parent_fd,
            self._parent.final_name,
        )
        self._owned_name = self._parent.final_name
        verify_parent_chain(self._parent)
        self._owned_name = None

    def cleanup(self) -> None:
        """Remove only the cold output inode held by this process."""
        if self.is_warm or self._owned_name is None:
            return
        remove_owned_tree(
            self._parent.parent_fd,
            self._root_fd,
            self._root_identity,
        )
        self._owned_name = None

    def close(self) -> None:
        """Close all retained descriptors exactly once."""
        if self._closed:
            return
        os.close(self._root_fd)
        close_descriptors(self._parent.descriptors)
        self._closed = True


def open_output_session(output_dir: Path, workspace_root: Path) -> OutputSession:
    """Open a warm output or create one descriptor-relative cold staging tree."""
    parent = open_parent_chain(output_dir, workspace_root)
    session: OutputSession | None = None
    try:
        verify_parent_chain(parent)
        try:
            root_fd = DirectoryFd(
                os.open(
                    parent.final_name,
                    directory_flags(),
                    dir_fd=parent.parent_fd,
                ),
            )
            try:
                _validate_warm_root(root_fd)
            except OutputLifecycleError:
                os.close(root_fd)
                raise
            session = OutputSession(parent, root_fd, None)
        except FileNotFoundError:
            stage_name = _create_private_stage(parent.parent_fd, parent.final_name)
            try:
                root_fd = DirectoryFd(
                    os.open(
                        stage_name,
                        directory_flags(),
                        dir_fd=parent.parent_fd,
                    ),
                )
            except OSError:
                os.rmdir(stage_name, dir_fd=parent.parent_fd)
                raise
            session = OutputSession(parent, root_fd, stage_name)
        verify_parent_chain(parent)
    except (OSError, OutputLifecycleError):
        if session is not None:
            session.cleanup()
            session.close()
        else:
            close_descriptors(parent.descriptors)
        raise
    else:
        return session


def _create_private_stage(parent_fd: DirectoryFd, final_name: str) -> str:
    for _attempt in range(32):
        name = f".{final_name}-{secrets.token_hex(12)}.tmp"
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            continue
        return name
    raise OutputLifecycleError(ERROR_STAGE_ALLOCATE)


def _validate_warm_root(root_fd: DirectoryFd) -> None:
    names = set(_directory_names(root_fd))
    if names != {"cache", "inspect-report.json"}:
        raise OutputLifecycleError(ERROR_FOREIGN)
    cache = os.stat("cache", dir_fd=root_fd, follow_symlinks=False)
    report = os.stat("inspect-report.json", dir_fd=root_fd, follow_symlinks=False)
    if not stat.S_ISDIR(cache.st_mode) or not stat.S_ISREG(report.st_mode):
        raise OutputLifecycleError(ERROR_UNSAFE)


def _directory_names(directory_fd: DirectoryFd) -> tuple[str, ...]:
    with os.scandir(directory_fd) as entries:
        return tuple(entry.name for entry in entries)
