# Copyright 2026 PSI Tool contributors
"""Immutable data structures for deterministic PSI inspect reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

REPORT_VERSION: Final = "psi-inspect-report-v2"
SHA256_LENGTH: Final = 64
RELATION_COUNT: Final = 7
Overall = Literal["PASS", "FAIL"]


@dataclass(frozen=True, slots=True)
class RelationReport:
    """One redacted expected-versus-actual cache relation result."""

    relation_id: str
    expected_shape: tuple[int, int]
    expected_schema: tuple[tuple[str, str], ...]
    actual_shape: tuple[int, int]
    actual_schema: tuple[tuple[str, str], ...]
    cache_key: str
    relation_hash: str
    expected_relation_hash: str
    parquet_sha256: str
    relative_path: str
    null_counts: tuple[tuple[str, int], ...]
    cache_hit: bool

    def is_parity_match(self) -> bool:
        """Return whether one cache record matches the golden contract."""
        return (
            self.expected_shape == self.actual_shape
            and self.expected_schema == self.actual_schema
            and len(self.cache_key) == SHA256_LENGTH
            and len(self.relation_hash) == SHA256_LENGTH
            and self.relation_hash == self.expected_relation_hash
            and len(self.parquet_sha256) == SHA256_LENGTH
            and self.relative_path.startswith("cache/")
        )


@dataclass(frozen=True, slots=True)
class InspectReport:
    """Immutable report content with deterministic identity."""

    manifest_sha256: str
    schema_version: str
    contract_version: str
    source_hashes: tuple[tuple[str, str], ...]
    relations: tuple[RelationReport, ...]
    elapsed_nanoseconds: int
    overall: Overall
    semantic_sha256: str
    failure: str | None = None
