# Copyright 2026 PSI Tool contributors
"""Safe errors and fixed messages for the source-contract boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, override

if TYPE_CHECKING:
    from pathlib import Path

ERROR_SINGLE_ROW_INDEX: Final = "single-row header strategy requires row_index"
ERROR_GROUPED_ROW_INDEXES: Final = (
    "grouped header strategy requires parent and child row indexes"
)
ERROR_GROUPED_NORMALIZATION: Final = (
    "grouped header strategy requires right parent fill and ' - ' separator"
)
ERROR_GROUPED_CONSTRUCTION: Final = (
    "grouped header strategy requires raw-header construction"
)
ERROR_PATH_TRAVERSAL: Final = "source path must be relative and traversal-free"
ERROR_PATH_ROOT: Final = "source path must start with PSI_SAMPLE_INPUT"
ERROR_CARRY_FRESH: Final = "carry-forward source cannot be fresh-required"
ERROR_CARRY_EVIDENCE: Final = (
    "carry-forward source requires reason and exact expected hash"
)
ERROR_CARRY_HASH: Final = "carry-forward expected hash must equal the source hash"
ERROR_NON_CARRY_METADATA: Final = (
    "non-carry-forward source cannot include carry-forward metadata"
)
ERROR_EMPTY_PROJECTION: Final = "relation projection cannot be empty"
ERROR_DUPLICATE_PROJECTION: Final = "relation projection canonical names must be unique"
ERROR_DUPLICATE_SOURCE_HEADER: Final = "relation projection has duplicate source header"
ERROR_SOURCES: Final = "manifest must contain exactly six known sources"
ERROR_RELATIONS: Final = "manifest must contain exactly seven known relation IDs"
ERROR_UNKNOWN_SOURCE: Final = "relation references an unknown source"
ERROR_SOURCE_FILE: Final = "source file is missing or outside workspace"
ERROR_SOURCE_HASH: Final = "source SHA-256 does not match manifest"
ERROR_SOURCE_OPEN: Final = "source workbook cannot be opened"
ERROR_SHEET: Final = "required sheet is missing"
ERROR_HEADER_SOURCE: Final = "header row is outside the source sheet"
ERROR_PHYSICAL_SHAPE: Final = "source physical extraction window shape does not match"
ERROR_LOGICAL_SHAPE: Final = "source logical extraction window shape does not match"
ERROR_HEADER_WINDOW: Final = "header row is outside the locked extraction window"
ERROR_GROUPED_WIDTH: Final = "grouped header rows have different widths"
ERROR_PROJECTED_HEADER_MISSING: Final = "projected header is missing"
ERROR_PROJECTED_HEADER_DUPLICATED: Final = "projected header is duplicated"
ERROR_NONBLANK_HEADER_COUNT: Final = "nonblank header count does not match"
ERROR_BLANK_SOURCE_COLUMN: Final = "declared blank source column is not blank"
ERROR_DISTINGUISHED_HEADER: Final = "distinguished source header does not match"


@dataclass(slots=True)
class ManifestLoadError(ValueError):
    """Describes one manifest-boundary failure without exposing source rows."""

    path: Path
    detail: str

    @override
    def __str__(self) -> str:
        """Render the manifest path and the safe contract failure detail."""
        return f"manifest {self.path}: {self.detail}"


@dataclass(slots=True)
class SourceContractError(ValueError):
    """Describes one invalid source-contract value."""

    detail: str

    @override
    def __str__(self) -> str:
        """Render the safe contract failure detail."""
        return self.detail
