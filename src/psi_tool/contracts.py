# Copyright 2026 PSI Tool contributors
"""Public API for the sanitized PSI golden-source contract."""

from __future__ import annotations

import hashlib
import io
import tomllib
from typing import TYPE_CHECKING

from pydantic import ValidationError

from ._contract_errors import ManifestLoadError, SourceContractError
from ._contract_models import (
    HeaderKind,
    HeaderStrategy,
    NonEmptyText,
    ProjectionField,
    RelationContract,
    RelationId,
    ResolvedSourceIdentity,
    Sha256,
    Shape,
    SourceManifest,
    SourceSpec,
    VerifiedManifest,
)
from ._workbook_validation import validate_workspace_sources

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "HeaderKind",
    "HeaderStrategy",
    "ManifestLoadError",
    "NonEmptyText",
    "ProjectionField",
    "RelationContract",
    "RelationId",
    "ResolvedSourceIdentity",
    "Sha256",
    "Shape",
    "SourceContractError",
    "SourceManifest",
    "SourceSpec",
    "VerifiedManifest",
    "load_manifest",
    "load_verified_manifest",
]


def load_verified_manifest(path: Path, workspace_root: Path) -> VerifiedManifest:
    """Read, identify, parse, and validate one immutable manifest snapshot."""
    if not workspace_root.is_absolute():
        raise ManifestLoadError(path=path, detail="workspace root must be absolute")
    root = workspace_root.resolve()
    manifest_path = path if path.is_absolute() else root / path
    manifest_path = manifest_path.resolve()
    try:
        content = manifest_path.read_bytes()
    except OSError as error:
        raise ManifestLoadError(path=path, detail="unable to read manifest") from error
    try:
        payload = tomllib.load(io.BytesIO(content))
    except tomllib.TOMLDecodeError as error:
        raise ManifestLoadError(path=path, detail="invalid TOML manifest") from error
    try:
        manifest = SourceManifest.model_validate(payload)
    except ValidationError as error:
        raise ManifestLoadError(path=path, detail=str(error)) from error
    try:
        sources = validate_workspace_sources(manifest, root)
    except SourceContractError as error:
        raise ManifestLoadError(path=path, detail=str(error)) from error
    return VerifiedManifest(
        manifest=manifest,
        manifest_sha256=hashlib.sha256(content).hexdigest(),
        workspace_root=root,
        sources=sources,
    )


def load_manifest(path: Path, workspace_root: Path) -> SourceManifest:
    """Return the parsed contract from one verified manifest snapshot."""
    return load_verified_manifest(path, workspace_root).manifest
