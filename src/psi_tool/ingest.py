# Copyright 2026 PSI Tool contributors
"""Exact-schema XLSX ingestion for PSI source relations."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, final, override

import polars as pl
from fastexcel import FastExcelError, read_excel

from ._workbook_validation import (
    load_locked_window,
    logical_data_start,
    normalized_headers,
    sha256_file,
    validate_header_metadata,
    validate_locked_shapes,
    validate_projected_headers,
)

if TYPE_CHECKING:
    from .contracts import RelationContract, VerifiedManifest


@final
class IngestError(ValueError):
    """Safe ingest failure without workbook row values."""

    __slots__: ClassVar[tuple[str, ...]] = ("detail",)
    detail: str

    def __init__(self, detail: str) -> None:
        """Initialize one safe boundary detail."""
        self.detail = detail
        super().__init__(detail)

    @override
    def __str__(self) -> str:
        return self.detail


def load_relation(
    verified: VerifiedManifest,
    relation: RelationContract,
) -> pl.DataFrame:
    """Decode one bounded worksheet window into its canonical string projection."""
    identity = verified.source_identity(relation.source_id)
    source_path = identity.path
    if (
        not source_path.is_relative_to(verified.workspace_root)
        or not source_path.is_file()
    ):
        raise IngestError(detail="source file is missing or outside workspace")
    if sha256_file(source_path) != identity.source.sha256:
        raise IngestError(detail="source SHA-256 does not match manifest")
    try:
        reader = read_excel(source_path)
    except FastExcelError as error:
        raise IngestError(detail="source workbook cannot be opened") from error
    if relation.sheet_name not in reader.sheet_names:
        raise IngestError(detail="required sheet is missing")
    try:
        raw = load_locked_window(reader, relation)
        validate_locked_shapes(relation, raw)
        headers = normalized_headers(raw, relation)
        validate_projected_headers(relation, headers)
        validate_header_metadata(relation.header_strategy, headers)
    except (FastExcelError, ValueError) as error:
        raise IngestError(detail=str(error)) from error
    source_columns = {
        header: raw.columns[index] for index, header in enumerate(headers) if header
    }
    projection = tuple(
        pl.col(source_columns[field.source_header])
        .cast(pl.String, strict=False)
        .alias(field.canonical_name)
        for field in relation.projection
    )
    frame = raw.slice(
        logical_data_start(relation.header_strategy),
        relation.logical_data_shape[0],
    ).select(projection)
    expected_shape = (relation.logical_data_shape[0], len(relation.projection))
    if frame.shape != expected_shape or any(
        dtype != pl.String for dtype in frame.dtypes
    ):
        raise IngestError(detail="canonical relation shape or dtype does not match")
    return frame
