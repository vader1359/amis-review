# Copyright 2026 PSI Tool contributors
"""Immutable Pydantic models for the sanitized source manifest."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date  # noqa: TC003 - Pydantic resolves this annotation at runtime.
from pathlib import Path  # noqa: TC003 - Pydantic resolves this annotation at runtime.
from typing import Annotated, ClassVar, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ._contract_errors import (
    ERROR_CARRY_EVIDENCE,
    ERROR_CARRY_FRESH,
    ERROR_CARRY_HASH,
    ERROR_DUPLICATE_PROJECTION,
    ERROR_DUPLICATE_SOURCE_HEADER,
    ERROR_EMPTY_PROJECTION,
    ERROR_GROUPED_CONSTRUCTION,
    ERROR_GROUPED_NORMALIZATION,
    ERROR_GROUPED_ROW_INDEXES,
    ERROR_NON_CARRY_METADATA,
    ERROR_PATH_ROOT,
    ERROR_PATH_TRAVERSAL,
    ERROR_RELATIONS,
    ERROR_SINGLE_ROW_INDEX,
    ERROR_SOURCES,
    ERROR_UNKNOWN_SOURCE,
    SourceContractError,
)

type RelationId = Literal[
    "crm_sales",
    "crm_sale_items",
    "product_master",
    "sales_detail_misa",
    "inventory",
    "purchase_po",
    "target",
]
type HeaderKind = Literal["single_row", "grouped_rows"]
type Shape = tuple[Annotated[int, Field(gt=0)], Annotated[int, Field(gt=0)]]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NonEmptyText = Annotated[str, Field(min_length=1)]

REQUIRED_RELATION_IDS: Final[frozenset[RelationId]] = frozenset(
    {
        "crm_sales",
        "crm_sale_items",
        "product_master",
        "sales_detail_misa",
        "inventory",
        "purchase_po",
        "target",
    },
)
REQUIRED_SOURCE_IDS: Final[frozenset[str]] = frozenset(
    {
        "crm_sale_workbook",
        "product_master_workbook",
        "sales_detail_misa_workbook",
        "inventory_workbook",
        "purchase_po_workbook",
        "target_workbook",
    },
)


class _FrozenContractModel(BaseModel):
    """Provides immutable, unknown-field-rejecting contract parsing."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)


class HeaderStrategy(_FrozenContractModel):
    """Defines either a single raw header row or a grouped-header construction."""

    kind: HeaderKind
    row_index: Annotated[int, Field(ge=0)] | None = None
    parent_row_index: Annotated[int, Field(ge=0)] | None = None
    child_row_index: Annotated[int, Field(ge=0)] | None = None
    source_row_offset: Annotated[int, Field(ge=0)] = 0
    nonblank_header_count: Annotated[int, Field(gt=0)] | None = None
    parent_fill: Literal["right"] | None = None
    separator: str | None = None
    raw_header_construction: str | None = None
    blank_column_numbers_one_based: tuple[Annotated[int, Field(gt=0)], ...] = ()
    distinguished_headers: tuple[tuple[Annotated[int, Field(gt=0)], str], ...] = ()

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        """Require strategy fields that match the declared header kind."""
        match self.kind:  # noqa: MATCH_OK -- basedpyright proves Literal exhaustion.
            case "single_row":
                if self.row_index is None:
                    raise SourceContractError(ERROR_SINGLE_ROW_INDEX)
            case "grouped_rows":
                if self.parent_row_index is None or self.child_row_index is None:
                    raise SourceContractError(ERROR_GROUPED_ROW_INDEXES)
                if self.parent_fill != "right" or self.separator != " - ":
                    raise SourceContractError(ERROR_GROUPED_NORMALIZATION)
                if self.raw_header_construction is None:
                    raise SourceContractError(ERROR_GROUPED_CONSTRUCTION)
        return self


class ProjectionField(_FrozenContractModel):
    """Maps one stable canonical field to its exact source header."""

    canonical_name: NonEmptyText
    source_header: NonEmptyText
    dtype: Literal["String"]


class SourceSpec(_FrozenContractModel):
    """Defines one immutable workbook identity and freshness policy."""

    source_id: NonEmptyText
    relative_path: Path
    sha256: Sha256
    fresh_required: bool
    carry_forward: bool
    carry_forward_sha256: Sha256 | None = None
    carry_forward_reason: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_source_policy(self) -> Self:
        """Reject traversal and incomplete or contradictory carry-forward metadata."""
        if self.relative_path.is_absolute() or ".." in self.relative_path.parts:
            raise SourceContractError(ERROR_PATH_TRAVERSAL)
        if (
            not self.relative_path.parts
            or self.relative_path.parts[0] != "PSI_SAMPLE_INPUT"
        ):
            raise SourceContractError(ERROR_PATH_ROOT)
        if self.carry_forward:
            if self.fresh_required:
                raise SourceContractError(ERROR_CARRY_FRESH)
            if self.carry_forward_reason is None or self.carry_forward_sha256 is None:
                raise SourceContractError(ERROR_CARRY_EVIDENCE)
            if self.carry_forward_sha256 != self.sha256:
                raise SourceContractError(ERROR_CARRY_HASH)
        elif (
            self.carry_forward_reason is not None
            or self.carry_forward_sha256 is not None
        ):
            raise SourceContractError(ERROR_NON_CARRY_METADATA)
        return self


@dataclass(frozen=True, slots=True)
class ResolvedSourceIdentity:
    """Binds one validated source contract to its canonical file path."""

    source: SourceSpec
    path: Path


class RelationContract(_FrozenContractModel):
    """Defines one sheet relation without any source-row data."""

    relation_id: RelationId
    source_id: NonEmptyText
    sheet_name: NonEmptyText
    physical_shape: Shape
    logical_data_shape: Shape
    expected_relation_sha256: Sha256
    header_strategy: HeaderStrategy
    projection: tuple[ProjectionField, ...]

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        """Require a nonempty projection with unique stable canonical field names."""
        canonical_names = tuple(field.canonical_name for field in self.projection)
        source_headers = tuple(field.source_header for field in self.projection)
        if not canonical_names:
            raise SourceContractError(ERROR_EMPTY_PROJECTION)
        if len(set(canonical_names)) != len(canonical_names):
            raise SourceContractError(ERROR_DUPLICATE_PROJECTION)
        if len(set(source_headers)) != len(source_headers):
            raise SourceContractError(ERROR_DUPLICATE_SOURCE_HEADER)
        return self

    def projection_source_header(self, canonical_name: str) -> str:
        """Return the exact source header for one canonical field."""
        for field in self.projection:
            if field.canonical_name == canonical_name:
                return field.source_header
        detail = f"unknown canonical projection field: {canonical_name}"
        raise SourceContractError(detail)


class SourceManifest(_FrozenContractModel):
    """Validates the complete seven-relation golden ingest contract."""

    schema_version: Literal["1.0"]
    contract_version: Literal["1.1"]
    relation_hash_algorithm: Literal["psi-semantic-string-v1"]
    as_of: date
    sources: tuple[SourceSpec, ...]
    relations: tuple[RelationContract, ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        """Reject missing, duplicate, or unknown sources and relation roles."""
        source_ids = tuple(source.source_id for source in self.sources)
        relation_ids = tuple(relation.relation_id for relation in self.relations)
        if frozenset(source_ids) != REQUIRED_SOURCE_IDS or len(source_ids) != len(
            REQUIRED_SOURCE_IDS,
        ):
            raise SourceContractError(ERROR_SOURCES)
        if frozenset(relation_ids) != REQUIRED_RELATION_IDS or len(relation_ids) != len(
            REQUIRED_RELATION_IDS,
        ):
            raise SourceContractError(ERROR_RELATIONS)
        known_source_ids = set(source_ids)
        if any(
            relation.source_id not in known_source_ids for relation in self.relations
        ):
            raise SourceContractError(ERROR_UNKNOWN_SOURCE)
        return self

    def relation(self, relation_id: RelationId) -> RelationContract:
        """Return one declared relation or fail closed on an unknown relation ID."""
        for relation in self.relations:
            if relation.relation_id == relation_id:
                return relation
        detail = f"unknown relation ID: {relation_id}"
        raise SourceContractError(detail)

    def source(self, source_id: str) -> SourceSpec:
        """Return one declared source or fail closed on an unknown source ID."""
        for source in self.sources:
            if source.source_id == source_id:
                return source
        detail = f"unknown source ID: {source_id}"
        raise SourceContractError(detail)

    def to_deterministic_json(self) -> str:
        """Serialize structural manifest metadata in deterministic key order."""
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


@dataclass(frozen=True, slots=True)
class VerifiedManifest:
    """Carries one byte-identity manifest and its validated source resolution."""

    manifest: SourceManifest
    manifest_sha256: str
    workspace_root: Path
    sources: tuple[ResolvedSourceIdentity, ...]

    def source_identity(self, source_id: str) -> ResolvedSourceIdentity:
        """Return one already-resolved source identity."""
        for identity in self.sources:
            if identity.source.source_id == source_id:
                return identity
        detail = f"unknown source ID: {source_id}"
        raise SourceContractError(detail)
