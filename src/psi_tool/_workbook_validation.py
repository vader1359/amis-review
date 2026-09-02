# Copyright 2026 PSI Tool contributors
"""Actual-workbook validation for the immutable source manifest."""

from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING, Final

from fastexcel import ExcelReader, FastExcelError, read_excel

from ._contract_errors import (
    ERROR_BLANK_SOURCE_COLUMN,
    ERROR_DISTINGUISHED_HEADER,
    ERROR_GROUPED_NORMALIZATION,
    ERROR_GROUPED_ROW_INDEXES,
    ERROR_GROUPED_WIDTH,
    ERROR_HEADER_SOURCE,
    ERROR_HEADER_WINDOW,
    ERROR_LOGICAL_SHAPE,
    ERROR_NONBLANK_HEADER_COUNT,
    ERROR_PHYSICAL_SHAPE,
    ERROR_PROJECTED_HEADER_DUPLICATED,
    ERROR_PROJECTED_HEADER_MISSING,
    ERROR_SHEET,
    ERROR_SINGLE_ROW_INDEX,
    ERROR_SOURCE_FILE,
    ERROR_SOURCE_HASH,
    ERROR_SOURCE_OPEN,
    SourceContractError,
)
from ._contract_models import ResolvedSourceIdentity

if TYPE_CHECKING:
    from pathlib import Path

    from polars import DataFrame

    from ._contract_models import (
        HeaderStrategy,
        RelationContract,
        SourceManifest,
    )

HASH_CHUNK_BYTES: Final = 1_048_576


def validate_workspace_sources(
    manifest: SourceManifest,
    workspace_root: Path,
) -> tuple[ResolvedSourceIdentity, ...]:
    """Verify source identities and workbook schemas without retaining row data."""
    root = workspace_root.resolve()
    source_paths: dict[str, Path] = {}
    identities: list[ResolvedSourceIdentity] = []
    for source in manifest.sources:
        source_path = (root / source.relative_path).resolve()
        if not source_path.is_relative_to(root) or not source_path.is_file():
            raise SourceContractError(ERROR_SOURCE_FILE)
        if sha256_file(source_path) != source.sha256:
            raise SourceContractError(ERROR_SOURCE_HASH)
        source_paths[source.source_id] = source_path
        identities.append(ResolvedSourceIdentity(source=source, path=source_path))
    for relation in manifest.relations:
        validate_relation_source(relation, source_paths[relation.source_id])
    return tuple(identities)


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 without retaining source bytes."""
    digest = sha256()
    with path.open("rb") as source_file:
        while chunk := source_file.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def validate_relation_source(relation: RelationContract, source_path: Path) -> None:
    """Verify one locked sheet window and its exact projected header schema."""
    try:
        reader = read_excel(source_path)
    except FastExcelError as error:
        raise SourceContractError(ERROR_SOURCE_OPEN) from error
    if relation.sheet_name not in reader.sheet_names:
        raise SourceContractError(ERROR_SHEET)
    frame = load_locked_window(reader, relation)
    validate_locked_shapes(relation, frame)
    headers = normalized_headers(frame, relation)
    validate_projected_headers(relation, headers)
    validate_header_metadata(relation.header_strategy, headers)


def load_locked_window(reader: ExcelReader, relation: RelationContract) -> DataFrame:
    """Read exactly the contract's structural window as strings through fastexcel."""
    try:
        sheet = reader.load_sheet_by_name(
            relation.sheet_name,
            header_row=None,
            n_rows=relation.physical_shape[0],
            schema_sample_rows=1,
            dtypes="string",
        )
    except FastExcelError as error:
        raise SourceContractError(ERROR_HEADER_SOURCE) from error
    return sheet.to_polars()


def validate_locked_shapes(relation: RelationContract, frame: DataFrame) -> None:
    """Check the locked extraction window and its strategy-derived logical shape."""
    if (frame.height, frame.width) != relation.physical_shape:
        raise SourceContractError(ERROR_PHYSICAL_SHAPE)
    data_start = logical_data_start(relation.header_strategy)
    if data_start > relation.physical_shape[0]:
        raise SourceContractError(ERROR_HEADER_WINDOW)
    expected_logical_shape = (
        relation.physical_shape[0] - data_start,
        relation.physical_shape[1],
    )
    if expected_logical_shape != relation.logical_data_shape:
        raise SourceContractError(ERROR_LOGICAL_SHAPE)


def logical_data_start(strategy: HeaderStrategy) -> int:
    """Return the locked data-start index without inspecting source-row values."""
    match strategy.kind:  # noqa: MATCH_OK -- basedpyright proves Literal exhaustion.
        case "single_row":
            if strategy.row_index is None:
                raise SourceContractError(ERROR_SINGLE_ROW_INDEX)
            return strategy.row_index + 1
        case "grouped_rows":
            if strategy.parent_row_index is None:
                raise SourceContractError(ERROR_GROUPED_ROW_INDEXES)
            return strategy.parent_row_index + 1


def normalized_headers(frame: DataFrame, relation: RelationContract) -> tuple[str, ...]:
    """Read only declared header rows and normalize grouped header structure."""
    strategy = relation.header_strategy
    match strategy.kind:  # noqa: MATCH_OK -- basedpyright proves Literal exhaustion.
        case "single_row":
            if strategy.row_index is None:
                raise SourceContractError(ERROR_SINGLE_ROW_INDEX)
            return header_row(
                frame,
                relation,
                strategy.row_index + strategy.source_row_offset,
            )
        case "grouped_rows":
            if strategy.parent_row_index is None or strategy.child_row_index is None:
                raise SourceContractError(ERROR_GROUPED_ROW_INDEXES)
            parent = header_row(
                frame,
                relation,
                strategy.parent_row_index + strategy.source_row_offset,
            )
            child = header_row(
                frame,
                relation,
                strategy.child_row_index + strategy.source_row_offset,
            )
            return flatten_grouped_headers(parent, child, strategy)


def header_row(
    frame: DataFrame,
    relation: RelationContract,
    row_index: int,
) -> tuple[str, ...]:
    """Return one bounded header row without exposing it outside validation."""
    if row_index >= relation.physical_shape[0]:
        raise SourceContractError(ERROR_HEADER_WINDOW)
    headers = normalize_header_cells(frame.row(row_index))
    if len(headers) != relation.physical_shape[1]:
        raise SourceContractError(ERROR_PHYSICAL_SHAPE)
    return headers


def normalize_header_cells(cells: tuple[str | None, ...]) -> tuple[str, ...]:
    """Convert one structural header row to exact strings and blank sentinels."""
    return tuple(
        unmangle_header(cell) if isinstance(cell, str) else "" for cell in cells
    )


def unmangle_header(header: str) -> str:
    """Remove fastexcel's generated duplicate suffix without changing source text."""
    if header.startswith("__UNNAMED__"):
        return ""
    prefix, marker, suffix = header.rpartition("_")
    return prefix if marker and suffix.isdigit() else header


def flatten_grouped_headers(
    parent: tuple[str, ...],
    child: tuple[str, ...],
    strategy: HeaderStrategy,
) -> tuple[str, ...]:
    """Apply the declared merged-parent fill and separator without business parsing."""
    if len(parent) != len(child):
        raise SourceContractError(ERROR_GROUPED_WIDTH)
    if strategy.separator is None:
        raise SourceContractError(ERROR_GROUPED_NORMALIZATION)
    current_parent = ""
    flattened: list[str] = []
    for parent_value, child_value in zip(parent, child, strict=True):
        if parent_value:
            current_parent = parent_value
        if child_value:
            flattened.append(
                f"{current_parent}{strategy.separator}{child_value}"
                if current_parent
                else child_value,
            )
        else:
            flattened.append(parent_value)
    return tuple(flattened)


def validate_projected_headers(
    relation: RelationContract,
    headers: tuple[str, ...],
) -> None:
    """Require each declared source header exactly once in the actual header schema."""
    for field in relation.projection:
        occurrences = headers.count(field.source_header)
        if occurrences == 0:
            raise SourceContractError(ERROR_PROJECTED_HEADER_MISSING)
        if occurrences > 1:
            raise SourceContractError(ERROR_PROJECTED_HEADER_DUPLICATED)


def validate_header_metadata(
    strategy: HeaderStrategy,
    headers: tuple[str, ...],
) -> None:
    """Check declared header counts, blanks, and distinguished source headers."""
    if (
        strategy.nonblank_header_count is not None
        and sum(bool(header.strip()) for header in headers)
        != strategy.nonblank_header_count
    ):
        raise SourceContractError(ERROR_NONBLANK_HEADER_COUNT)
    for column_number in strategy.blank_column_numbers_one_based:
        if column_number > len(headers) or headers[column_number - 1]:
            raise SourceContractError(ERROR_BLANK_SOURCE_COLUMN)
    for column_number, expected_header in strategy.distinguished_headers:
        if (
            column_number > len(headers)
            or headers[column_number - 1] != expected_header
        ):
            raise SourceContractError(ERROR_DISTINGUISHED_HEADER)
