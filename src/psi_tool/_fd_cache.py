# Copyright 2026 PSI Tool contributors
"""Descriptor-relative Parquet cache I/O for an inspect output root."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from . import ingest
from ._cache_errors import CacheIntegrityError, CachePathError
from ._cache_hash import METADATA_PREFIX, cache_key, semantic_hash
from ._cache_models import (
    ColumnNullCount,
    ColumnSchema,
    RelationCacheMetadata,
    embedded_metadata,
)
from ._fd_types import DirectoryFd

if TYPE_CHECKING:
    from .contracts import RelationContract, VerifiedManifest


@dataclass(frozen=True, slots=True)
class _Context:
    relation: RelationContract
    cache_key: str
    name: str


def materialize_cache(
    verified: VerifiedManifest,
    output_root_fd: DirectoryFd,
) -> tuple[RelationCacheMetadata, ...]:
    """Create or verify the complete cache through directory descriptors."""
    contexts = tuple(
        _Context(
            relation=relation,
            cache_key=(key := cache_key(verified.manifest, relation)),
            name=f"{relation.relation_id}-{key}.parquet",
        )
        for relation in verified.manifest.relations
    )
    cache_fd, cache_hit = _open_cache(output_root_fd)
    try:
        if cache_hit:
            _validate_names(cache_fd, tuple(item.name for item in contexts))
            return tuple(_read_relation(cache_fd, context) for context in contexts)
        return tuple(
            _write_relation(
                cache_fd,
                context,
                ingest.load_relation(verified, context.relation),
            )
            for context in contexts
        )
    finally:
        os.close(cache_fd)


def _open_cache(output_root_fd: DirectoryFd) -> tuple[DirectoryFd, bool]:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        return DirectoryFd(os.open("cache", flags, dir_fd=output_root_fd)), True
    except FileNotFoundError:
        try:
            os.mkdir("cache", mode=0o700, dir_fd=output_root_fd)
            descriptor = os.open("cache", flags, dir_fd=output_root_fd)
        except OSError as error:
            raise CachePathError(
                detail="cache root contains unsafe foreign state",
            ) from error
        return DirectoryFd(descriptor), False
    except OSError as error:
        raise CachePathError(
            detail="cache root contains unsafe foreign state",
        ) from error


def _validate_names(cache_fd: DirectoryFd, expected: tuple[str, ...]) -> None:
    names = _directory_names(cache_fd)
    if set(names) != set(expected):
        raise CachePathError(
            detail="cache root is incomplete or contains foreign state",
        )
    for name in names:
        item = os.stat(name, dir_fd=cache_fd, follow_symlinks=False)
        if not stat.S_ISREG(item.st_mode):
            raise CachePathError(detail="cache root contains unsafe foreign state")


def _write_relation(
    cache_fd: DirectoryFd,
    context: _Context,
    frame: pl.DataFrame,
) -> RelationCacheMetadata:
    metadata = _frame_metadata(frame, context, "", cache_hit=False)
    if metadata.relation_hash != context.relation.expected_relation_sha256:
        raise CacheIntegrityError(
            detail="cache content does not match trusted manifest relation hash",
        )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = os.open(context.name, flags, 0o600, dir_fd=cache_fd)
    with os.fdopen(descriptor, "wb") as handle:
        _ = frame.write_parquet(
            handle,
            compression="zstd",
            statistics=True,
            metadata=embedded_metadata(metadata),
        )
        handle.flush()
        os.fsync(handle.fileno())
    return replace(metadata, parquet_sha256=_sha256_at(cache_fd, context.name))


def _read_relation(
    cache_fd: DirectoryFd,
    context: _Context,
) -> RelationCacheMetadata:
    descriptor = os.open(context.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=cache_fd)
    try:
        with os.fdopen(descriptor, "rb") as handle:
            embedded = pl.read_parquet_metadata(handle)
            _ = handle.seek(0)
            frame = pl.read_parquet(handle)
    except (OSError, pl.exceptions.PolarsError) as error:
        raise CacheIntegrityError(
            detail="cache Parquet is corrupt or unreadable",
        ) from error
    actual = _frame_metadata(
        frame,
        context,
        _sha256_at(cache_fd, context.name),
        cache_hit=True,
    )
    if actual.relation_hash != context.relation.expected_relation_sha256:
        raise CacheIntegrityError(
            detail="cache content does not match trusted manifest relation hash",
        )
    cache_metadata = {
        key: value for key, value in embedded.items() if key.startswith(METADATA_PREFIX)
    }
    if cache_metadata != embedded_metadata(actual):
        raise CacheIntegrityError(detail="cache metadata or content does not match")
    return actual


def _frame_metadata(
    frame: pl.DataFrame,
    context: _Context,
    parquet_sha256: str,
    *,
    cache_hit: bool,
) -> RelationCacheMetadata:
    return RelationCacheMetadata(
        relation_id=context.relation.relation_id,
        cache_key=context.cache_key,
        relation_hash=semantic_hash(frame),
        parquet_sha256=parquet_sha256,
        schema=tuple(
            ColumnSchema(name=name, dtype=str(dtype))
            for name, dtype in zip(frame.columns, frame.dtypes, strict=True)
        ),
        rows=frame.height,
        columns=frame.width,
        null_counts=tuple(
            ColumnNullCount(name=name, null_count=frame[name].null_count())
            for name in frame.columns
        ),
        relative_path=Path(context.name),
        cache_hit=cache_hit,
    )


def _sha256_at(directory_fd: DirectoryFd, name: str) -> str:
    digest = hashlib.sha256()
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
    with os.fdopen(descriptor, "rb") as handle:
        while chunk := handle.read(1_048_576):
            digest.update(chunk)
    return digest.hexdigest()


def _directory_names(directory_fd: DirectoryFd) -> tuple[str, ...]:
    with os.scandir(directory_fd) as entries:
        return tuple(entry.name for entry in entries)
