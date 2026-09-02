# Copyright 2026 PSI Tool contributors
"""Deterministic, redacted inspect-report construction and publication."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from ._report_json import serialize_report
from ._report_models import (
    RELATION_COUNT,
    REPORT_VERSION,
    InspectReport,
    Overall,
    RelationReport,
)

if TYPE_CHECKING:
    from ._cache_models import RelationCacheMetadata
    from ._fd_types import DirectoryFd
    from .contracts import RelationContract, SourceManifest, VerifiedManifest


def build_inspect_report(
    verified: VerifiedManifest,
    metadata: tuple[RelationCacheMetadata, ...],
    elapsed_nanoseconds: int,
) -> InspectReport:
    """Build golden parity output from verified cache metadata only."""
    manifest = verified.manifest
    relation_reports = _relation_reports(manifest, metadata)
    required_ids = tuple(relation.relation_id for relation in manifest.relations)
    metadata_ids = tuple(item.relation_id for item in metadata)
    is_complete = metadata_ids == required_ids and len(metadata) == RELATION_COUNT
    is_match = is_complete and all(item.is_parity_match() for item in relation_reports)
    overall: Overall = "PASS" if is_match else "FAIL"
    draft = InspectReport(
        manifest_sha256=verified.manifest_sha256,
        schema_version=manifest.schema_version,
        contract_version=manifest.contract_version,
        source_hashes=tuple((item.source_id, item.sha256) for item in manifest.sources),
        relations=relation_reports,
        elapsed_nanoseconds=elapsed_nanoseconds,
        overall=overall,
        semantic_sha256="",
    )
    return InspectReport(
        manifest_sha256=draft.manifest_sha256,
        schema_version=draft.schema_version,
        contract_version=draft.contract_version,
        source_hashes=draft.source_hashes,
        relations=draft.relations,
        elapsed_nanoseconds=draft.elapsed_nanoseconds,
        overall=draft.overall,
        semantic_sha256=semantic_sha256(draft),
    )


def build_failure_report() -> InspectReport:
    """Build a deterministic report that cannot be confused with a prior PASS."""
    draft = InspectReport(
        manifest_sha256="",
        schema_version="",
        contract_version="",
        source_hashes=(),
        relations=(),
        elapsed_nanoseconds=0,
        overall="FAIL",
        semantic_sha256="",
        failure="validation_failed",
    )
    return InspectReport(
        manifest_sha256=draft.manifest_sha256,
        schema_version=draft.schema_version,
        contract_version=draft.contract_version,
        source_hashes=draft.source_hashes,
        relations=draft.relations,
        elapsed_nanoseconds=draft.elapsed_nanoseconds,
        overall=draft.overall,
        semantic_sha256=semantic_sha256(draft),
        failure=draft.failure,
    )


def semantic_sha256(report: InspectReport) -> str:
    """Hash only invariant contract and logical parity evidence."""
    canonical = {
        "contract_version": report.contract_version,
        "manifest_sha256": report.manifest_sha256,
        "overall": report.overall,
        "relations": [
            {
                "actual": [item.actual_shape, item.actual_schema],
                "expected": [item.expected_shape, item.expected_schema],
                "relation_hash": item.relation_hash,
                "expected_relation_hash": item.expected_relation_hash,
                "relation_id": item.relation_id,
            }
            for item in report.relations
        ],
        "report_version": REPORT_VERSION,
        "schema_version": report.schema_version,
        "source_hashes": report.source_hashes,
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_report_atomic(
    directory_fd: DirectoryFd,
    name: str,
    report: InspectReport,
) -> None:
    """Durably replace one report relative to an owned directory descriptor."""
    temporary_name = f".{name}-{secrets.token_hex(12)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            _ = handle.write(serialize_report(report))
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(
            temporary_name,
            name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
    finally:
        with suppress(FileNotFoundError):
            os.unlink(temporary_name, dir_fd=directory_fd)


def _relation_reports(
    manifest: SourceManifest,
    metadata: tuple[RelationCacheMetadata, ...],
) -> tuple[RelationReport, ...]:
    by_id = {item.relation_id: item for item in metadata}
    return tuple(
        _relation_report(relation, by_id.get(relation.relation_id))
        for relation in manifest.relations
    )


def _relation_report(
    relation: RelationContract,
    metadata: RelationCacheMetadata | None,
) -> RelationReport:
    expected_schema = tuple(
        (field.canonical_name, field.dtype) for field in relation.projection
    )
    if metadata is None:
        return RelationReport(
            relation_id=relation.relation_id,
            expected_shape=(relation.logical_data_shape[0], len(expected_schema)),
            expected_schema=expected_schema,
            actual_shape=(0, 0),
            actual_schema=(),
            cache_key="",
            relation_hash="",
            expected_relation_hash=relation.expected_relation_sha256,
            parquet_sha256="",
            relative_path="",
            null_counts=(),
            cache_hit=False,
        )
    return RelationReport(
        relation_id=metadata.relation_id,
        expected_shape=(relation.logical_data_shape[0], len(expected_schema)),
        expected_schema=expected_schema,
        actual_shape=(metadata.rows, metadata.columns),
        actual_schema=tuple((item.name, item.dtype) for item in metadata.schema),
        cache_key=metadata.cache_key,
        relation_hash=metadata.relation_hash,
        expected_relation_hash=relation.expected_relation_sha256,
        parquet_sha256=metadata.parquet_sha256,
        relative_path=(Path("cache") / metadata.relative_path).as_posix(),
        null_counts=tuple(
            (item.name, item.null_count) for item in metadata.null_counts
        ),
        cache_hit=metadata.cache_hit,
    )
