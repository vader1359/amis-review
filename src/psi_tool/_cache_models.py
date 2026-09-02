# Copyright 2026 PSI Tool contributors
"""Immutable redacted models stored alongside PSI cache relations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._cache_hash import METADATA_PREFIX, SEMANTIC_HASH_VERSION

if TYPE_CHECKING:
    from pathlib import Path

    from .contracts import RelationId


@dataclass(frozen=True, slots=True)
class ColumnSchema:
    """One ordered canonical Parquet column."""

    name: str
    dtype: str


@dataclass(frozen=True, slots=True)
class ColumnNullCount:
    """Aggregate null count for one canonical column."""

    name: str
    null_count: int


@dataclass(frozen=True, slots=True)
class RelationCacheMetadata:
    """Redacted deterministic metadata for one cached relation."""

    relation_id: RelationId
    cache_key: str
    relation_hash: str
    parquet_sha256: str
    schema: tuple[ColumnSchema, ...]
    rows: int
    columns: int
    null_counts: tuple[ColumnNullCount, ...]
    relative_path: Path
    cache_hit: bool

    def stable_fields(self) -> str:
        """Return deterministic metadata excluding the run-local hit status."""
        return json.dumps(
            {
                "cache_key": self.cache_key,
                "columns": self.columns,
                "null_counts": [
                    [item.name, item.null_count] for item in self.null_counts
                ],
                "parquet_sha256": self.parquet_sha256,
                "relation_hash": self.relation_hash,
                "relation_id": self.relation_id,
                "relative_path": self.relative_path.as_posix(),
                "rows": self.rows,
                "schema": [[item.name, item.dtype] for item in self.schema],
            },
            separators=(",", ":"),
            sort_keys=True,
        )


def embedded_metadata(metadata: RelationCacheMetadata) -> dict[str, str]:
    """Encode redacted integrity fields into Parquet key-value metadata."""
    return {
        f"{METADATA_PREFIX}cache_key": metadata.cache_key,
        f"{METADATA_PREFIX}columns": str(metadata.columns),
        f"{METADATA_PREFIX}null_counts": json.dumps(
            [[item.name, item.null_count] for item in metadata.null_counts],
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        f"{METADATA_PREFIX}relation_hash": metadata.relation_hash,
        f"{METADATA_PREFIX}relation_id": metadata.relation_id,
        f"{METADATA_PREFIX}rows": str(metadata.rows),
        f"{METADATA_PREFIX}semantic_hash_version": SEMANTIC_HASH_VERSION,
        f"{METADATA_PREFIX}schema": json.dumps(
            [[item.name, item.dtype] for item in metadata.schema],
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
