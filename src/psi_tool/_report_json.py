# Copyright 2026 PSI Tool contributors

from __future__ import annotations

import json
from typing import TypedDict

from ._report_models import REPORT_VERSION, InspectReport, RelationReport


class _ShapePayload(TypedDict):
    schema: list[list[str]]
    shape: list[int]


class _RelationPayload(TypedDict):
    actual: _ShapePayload
    cache_hit: bool
    cache_key: str
    expected: _ShapePayload
    null_counts: list[list[str | int]]
    parquet_sha256: str
    relation_hash: str
    expected_relation_hash: str
    relation_id: str
    relative_cache_path: str


def serialize_report(report: InspectReport) -> str:
    payload = {
        "contract_version": report.contract_version,
        "execution": {
            "cache_status": _cache_status(report.relations),
            "phase_timings_ms": {
                "materialize_cache": report.elapsed_nanoseconds / 1_000_000,
            },
        },
        "failure": report.failure,
        "manifest": {
            "sha256": report.manifest_sha256,
            "source_sha256": [list(item) for item in report.source_hashes],
        },
        "overall": report.overall,
        "relations": [_relation_payload(item) for item in report.relations],
        "report_version": REPORT_VERSION,
        "schema_version": report.schema_version,
        "semantic_sha256": report.semantic_sha256,
    }
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def _relation_payload(
    relation: RelationReport,
) -> _RelationPayload:
    return {
        "actual": {
            "schema": [list(item) for item in relation.actual_schema],
            "shape": list(relation.actual_shape),
        },
        "cache_hit": relation.cache_hit,
        "cache_key": relation.cache_key,
        "expected": {
            "schema": [list(item) for item in relation.expected_schema],
            "shape": list(relation.expected_shape),
        },
        "null_counts": [list(item) for item in relation.null_counts],
        "parquet_sha256": relation.parquet_sha256,
        "relation_hash": relation.relation_hash,
        "expected_relation_hash": relation.expected_relation_hash,
        "relation_id": relation.relation_id,
        "relative_cache_path": relation.relative_path,
    }


def _cache_status(relations: tuple[RelationReport, ...]) -> str:
    return "warm" if relations and all(item.cache_hit for item in relations) else "cold"
