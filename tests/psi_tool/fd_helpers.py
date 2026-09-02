# Copyright 2026 PSI Tool contributors
from __future__ import annotations

import os
import shutil
from contextlib import contextmanager
from typing import TYPE_CHECKING

from psi_tool._fd_types import DirectoryFd
from psi_tool._fd_walk import directory_flags
from psi_tool.cache import materialize_cache

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from psi_tool._cache_models import RelationCacheMetadata
    from psi_tool.contracts import VerifiedManifest


@contextmanager
def opened_directory(path: Path) -> Generator[DirectoryFd]:
    descriptor = DirectoryFd(os.open(path, directory_flags()))
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def materialize_cache_path(
    verified: VerifiedManifest,
    cache_root: Path,
) -> tuple[RelationCacheMetadata, ...]:
    assert cache_root.name == "cache"
    existed = cache_root.exists() or cache_root.is_symlink()
    with opened_directory(cache_root.parent) as parent_fd:
        try:
            return materialize_cache(verified, parent_fd)
        except (OSError, ValueError):
            if not existed and cache_root.is_dir():
                shutil.rmtree(cache_root)
            raise
