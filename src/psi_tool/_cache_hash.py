# Copyright 2026 PSI Tool contributors
"""Deterministic cache identity and logical string hashing."""

from __future__ import annotations

import hashlib
import io
import json
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

if TYPE_CHECKING:
    from pathlib import Path

    from .contracts import RelationContract, SourceManifest

CACHE_FORMAT_VERSION: Final = "psi-parquet-cache-v2"
SEMANTIC_HASH_VERSION: Final = "psi-semantic-string-v1"
METADATA_PREFIX: Final = "psi."


def cache_key(manifest: SourceManifest, relation: RelationContract) -> str:
    """Hash every structural input that defines one relation cache identity."""
    source = manifest.source(relation.source_id)
    identity = {
        "cache_format": CACHE_FORMAT_VERSION,
        "contract_version": manifest.contract_version,
        "dtype_contract": [field.dtype for field in relation.projection],
        "header_strategy": relation.header_strategy.model_dump(mode="json"),
        "logical_data_shape": relation.logical_data_shape,
        "physical_shape": relation.physical_shape,
        "projection": [
            [field.source_header, field.canonical_name] for field in relation.projection
        ],
        "relation_id": relation.relation_id,
        "expected_relation_sha256": relation.expected_relation_sha256,
        "schema_version": manifest.schema_version,
        "semantic_hash_version": SEMANTIC_HASH_VERSION,
        "sheet_name": relation.sheet_name,
        "source_sha256": source.sha256,
    }
    encoded = json.dumps(
        identity,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def semantic_hash(frame: pl.DataFrame) -> str:
    """Hash ordered strings with explicit null and length-prefixed boundaries."""
    schema = json.dumps(
        [
            [name, str(dtype)]
            for name, dtype in zip(frame.columns, frame.dtypes, strict=True)
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    digest = hashlib.sha256()
    prefix = SEMANTIC_HASH_VERSION.encode()
    digest.update(len(prefix).to_bytes(8, "big"))
    digest.update(prefix)
    digest.update(frame.height.to_bytes(8, "big"))
    digest.update(len(schema).to_bytes(8, "big"))
    digest.update(schema)
    for name in frame.columns:
        name_bytes = name.encode()
        digest.update(len(name_bytes).to_bytes(8, "big"))
        digest.update(name_bytes)
        series = frame.get_column(name)
        null_bitmap = (
            series.is_null()
            .cast(pl.UInt8)
            .to_numpy()
            .astype(np.dtype("u1"), copy=False)
            .tobytes()
        )
        digest.update(len(null_bitmap).to_bytes(8, "big"))
        digest.update(null_bitmap)
        text_buffer = io.StringIO()
        series.fill_null("").to_frame().write_csv(
            text_buffer,
            include_header=False,
            quote_style="always",
        )
        text_bytes = text_buffer.getvalue().encode()
        digest.update(len(text_bytes).to_bytes(8, "big"))
        digest.update(text_bytes)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    """Return the streaming SHA-256 for one materialized cache file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1_048_576):
            digest.update(chunk)
    return digest.hexdigest()
