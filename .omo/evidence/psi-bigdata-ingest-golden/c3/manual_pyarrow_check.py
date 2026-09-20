# Copyright 2026 PSI Tool contributors
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "numpy>=2.0.0",
#   "pyarrow>=17.0.0",
#   "typer>=0.15.0",
# ]
# ///
# ─── How to run ───
# uv run manual_pyarrow_check.py MANIFEST_PATH CACHE_ROOT
"""Reproducible independent PyArrow verification for the seven PSI caches."""

from __future__ import annotations

import json
import pathlib
import tomllib
from typing import ClassVar, Final, final, override

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import typer

EXPECTED_RELATIONS: Final = 7
SHA256_LENGTH: Final = 64


@final
class CheckError(ValueError):
    """One redacted independent cache verification failure."""

    __slots__: ClassVar[tuple[str, ...]] = ("detail",)
    detail: str

    def __init__(self, detail: str) -> None:
        """Initialize a redacted verification detail."""
        self.detail = detail
        super().__init__(detail)

    @override
    def __str__(self) -> str:
        return self.detail


def _require(*, condition: bool, detail: str) -> None:
    if not condition:
        raise CheckError(detail=detail)


def check(manifest: str, cache_root: str) -> None:
    """Verify all cached relations through PyArrow without reading row values."""
    manifest_path = pathlib.Path(manifest)
    cache_path = pathlib.Path(cache_root)
    payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    expected_relations = {
        relation["relation_id"]: relation for relation in payload["relations"]
    }
    parquet_paths = tuple(sorted(cache_path.glob("*.parquet")))
    _require(
        condition=len(parquet_paths) == EXPECTED_RELATIONS,
        detail="expected exactly seven Parquet files",
    )
    summaries: list[dict[str, str | int | bool]] = []
    seen: set[str] = set()
    for path in parquet_paths:
        table = pq.read_table(path)
        raw_metadata = pq.ParquetFile(path).metadata.metadata
        _require(
            condition=raw_metadata is not None,
            detail="Parquet metadata is missing",
        )
        metadata = {
            key.decode(): value.decode()
            for key, value in raw_metadata.items()
            if key.startswith(b"psi.")
        }
        relation_id = metadata.get("psi.relation_id", "")
        _require(
            condition=relation_id in expected_relations,
            detail="unknown relation metadata",
        )
        expected = expected_relations[relation_id]
        names = tuple(field["canonical_name"] for field in expected["projection"])
        rows = expected["logical_data_shape"][0]
        null_counts = tuple(column.null_count for column in table.columns)
        embedded_schema = json.loads(metadata.get("psi.schema", "[]"))
        embedded_nulls = json.loads(metadata.get("psi.null_counts", "[]"))
        _require(
            condition=tuple(table.column_names) == names,
            detail="ordered schema mismatch",
        )
        _require(condition=table.num_rows == rows, detail="row count mismatch")
        _require(
            condition=table.num_columns == len(names),
            detail="column count mismatch",
        )
        _require(
            condition=all(
                pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
                for field in table.schema
            ),
            detail="non-string Arrow field",
        )
        _require(
            condition=embedded_schema == [[name, "String"] for name in names],
            detail="embedded schema mismatch",
        )
        _require(
            condition=embedded_nulls
            == [[name, count] for name, count in zip(names, null_counts, strict=True)],
            detail="embedded null counts mismatch",
        )
        _require(
            condition=metadata.get("psi.rows") == str(rows),
            detail="embedded rows mismatch",
        )
        _require(
            condition=metadata.get("psi.columns") == str(len(names)),
            detail="embedded columns mismatch",
        )
        _require(
            condition=metadata.get("psi.semantic_hash_version")
            == "psi-semantic-string-v1",
            detail="semantic hash version mismatch",
        )
        cache_key = metadata.get("psi.cache_key", "")
        relation_hash = metadata.get("psi.relation_hash", "")
        _require(
            condition=len(cache_key) == SHA256_LENGTH,
            detail="cache key is invalid",
        )
        _require(
            condition=len(relation_hash) == SHA256_LENGTH,
            detail="relation hash is invalid",
        )
        _require(
            condition=path.name == f"{relation_id}-{cache_key}.parquet",
            detail="content-addressed filename mismatch",
        )
        seen.add(relation_id)
        summaries.append(
            {
                "all_string": True,
                "columns": table.num_columns,
                "null_counts": True,
                "ordered_schema": True,
                "relation_id": relation_id,
                "rows": table.num_rows,
            },
        )
    _require(
        condition=seen == set(expected_relations),
        detail="relation set mismatch",
    )
    typer.echo(
        json.dumps(
            {
                "numpy_version": np.__version__,
                "relations": summaries,
                "status": "PASS",
                "verified": len(summaries),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    typer.run(check)
