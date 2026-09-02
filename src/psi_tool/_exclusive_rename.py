# Copyright 2026 PSI Tool contributors
"""Native exclusive directory rename for supported POSIX runtimes."""

from __future__ import annotations

import ctypes
import errno
import sys
from typing import Final, Protocol, final

DARWIN_RENAME_EXCL: Final = 0x00000004
LINUX_RENAME_NOREPLACE: Final = 0x00000001


class _NativeRename(Protocol):
    def __call__(
        self,
        source_dir_fd: int,
        source_name: bytes,
        destination_dir_fd: int,
        destination_name: bytes,
        flags: int,
    ) -> int: ...


@final
class _DarwinRename:
    __slots__ = ("_native",)
    _native: _NativeRename

    def __init__(self, library: ctypes.CDLL) -> None:
        prototype = ctypes.CFUNCTYPE(
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        self._native = prototype(("renameatx_np", library))

    def invoke(
        self,
        source_dir_fd: int,
        source_name: str,
        destination_dir_fd: int,
        destination_name: str,
    ) -> int:
        return self._native(
            source_dir_fd,
            source_name.encode(),
            destination_dir_fd,
            destination_name.encode(),
            DARWIN_RENAME_EXCL,
        )


@final
class _LinuxRename:
    __slots__ = ("_native",)
    _native: _NativeRename

    def __init__(self, library: ctypes.CDLL) -> None:
        prototype = ctypes.CFUNCTYPE(
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        self._native = prototype(("renameat2", library))

    def invoke(
        self,
        source_dir_fd: int,
        source_name: str,
        destination_dir_fd: int,
        destination_name: str,
    ) -> int:
        return self._native(
            source_dir_fd,
            source_name.encode(),
            destination_dir_fd,
            destination_name.encode(),
            LINUX_RENAME_NOREPLACE,
        )


def rename_exclusive(
    source_dir_fd: int,
    source_name: str,
    destination_dir_fd: int,
    destination_name: str,
) -> None:
    """Rename without replacement or fail closed when unavailable."""
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        result = _DarwinRename(library).invoke(
            source_dir_fd,
            source_name,
            destination_dir_fd,
            destination_name,
        )
    elif sys.platform.startswith("linux"):
        result = _LinuxRename(library).invoke(
            source_dir_fd,
            source_name,
            destination_dir_fd,
            destination_name,
        )
    else:
        raise OSError(errno.ENOTSUP, "exclusive directory publication unsupported")
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, "exclusive output publication failed")
