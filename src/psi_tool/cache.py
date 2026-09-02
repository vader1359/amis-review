# Copyright 2026 PSI Tool contributors
"""Descriptor-owned cache API and deterministic cache metadata helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._cache_errors import CacheIntegrityError, CachePathError
from ._cache_hash import semantic_hash
from ._cache_models import ColumnNullCount, ColumnSchema, RelationCacheMetadata
from ._fd_cache import materialize_cache

if TYPE_CHECKING:
    import polars as pl

__all__ = (
    "CacheIntegrityError",
    "CachePathError",
    "ColumnNullCount",
    "ColumnSchema",
    "RelationCacheMetadata",
    "materialize_cache",
    "relation_hash",
)


def relation_hash(frame: pl.DataFrame) -> str:
    """Return the stable logical hash used by relation pins."""
    return semantic_hash(frame)
