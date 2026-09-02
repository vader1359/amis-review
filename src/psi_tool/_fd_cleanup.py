# Copyright 2026 PSI Tool contributors
"""No-follow removal of one descriptor-owned private directory tree."""

from __future__ import annotations

import errno
import os
import stat

from ._fd_types import DirectoryFd
from ._fd_walk import directory_flags

type FileIdentity = tuple[int, int]


def remove_owned_tree(
    parent_fd: DirectoryFd,
    root_fd: DirectoryFd,
    identity: FileIdentity,
) -> None:
    _remove_tree_contents(root_fd)
    owned_name = _find_identity_name(parent_fd, identity)
    if owned_name is None:
        return
    try:
        os.rmdir(owned_name, dir_fd=parent_fd)
    except OSError:
        return


def _find_identity_name(
    parent_fd: DirectoryFd,
    identity: FileIdentity,
) -> str | None:
    for name in _directory_names(parent_fd):
        try:
            item = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if stat.S_ISDIR(item.st_mode) and (item.st_dev, item.st_ino) == identity:
            return name
    return None


def _remove_tree_contents(directory_fd: DirectoryFd) -> None:
    for name in _directory_names(directory_fd):
        item = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if stat.S_ISDIR(item.st_mode):
            child_fd = DirectoryFd(
                os.open(name, directory_flags(), dir_fd=directory_fd),
            )
            try:
                _remove_tree_contents(child_fd)
            finally:
                os.close(child_fd)
            os.rmdir(name, dir_fd=directory_fd)
        else:
            try:
                os.unlink(name, dir_fd=directory_fd)
            except OSError as error:
                if error.errno != errno.ENOENT:
                    raise


def _directory_names(directory_fd: DirectoryFd) -> tuple[str, ...]:
    with os.scandir(directory_fd) as entries:
        return tuple(entry.name for entry in entries)
