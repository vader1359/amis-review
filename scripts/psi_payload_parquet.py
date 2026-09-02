from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import ClassVar, Final

import numpy as np
import polars as pl
import typer
from pydantic import BaseModel, ConfigDict, JsonValue, RootModel, TypeAdapter

FORMAT_VERSION: Final = 1
PAYLOAD_ADAPTER: Final = TypeAdapter(dict[str, JsonValue])
ROW_ADAPTER: Final = TypeAdapter(dict[str, object])


class TableSpec(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    file: str
    kind: str
    columns: list[str]
    width: int
    rows: int
    sha256: str


class BundleManifest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    format_version: int
    source_sha256: str
    engines: dict[str, str]
    scalars: dict[str, JsonValue]
    tables: dict[str, TableSpec]


class JsonRoot(RootModel[JsonValue]):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)


class BundleVersionError(ValueError):
    pass


class ChecksumError(ValueError):
    pass


app = typer.Typer(add_completion=False)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _encoded(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decoded(value: object) -> JsonValue:
    return JsonRoot.model_validate_json(str(value)).root


@app.command()
def pack(source: Path, output_dir: Path) -> None:
    payload = PAYLOAD_ADAPTER.validate_json(source.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    scalars: dict[str, JsonValue] = {}
    tables: dict[str, TableSpec] = {}

    for key, value in payload.items():
        if not isinstance(value, list):
            scalars[key] = value
            continue

        first = value[0] if value else None
        kind = "dict" if isinstance(first, dict) else "matrix"
        columns = list(first) if isinstance(first, dict) else []
        width = len(first) if isinstance(first, list) else 0
        data: dict[str, pl.Series] = {
            "_row": pl.Series("_row", np.arange(len(value), dtype=np.int64))
        }
        if isinstance(first, dict):
            for column in columns:
                data[column] = pl.Series(
                    column,
                    [
                        _encoded(row.get(column))
                        for row in value
                        if isinstance(row, dict)
                    ],
                    pl.String,
                )
        else:
            for index in range(width):
                name = f"c{index:03d}"
                data[name] = pl.Series(
                    name,
                    [_encoded(row[index]) for row in value if isinstance(row, list)],
                    pl.String,
                )

        table_path = output_dir / f"{key}.parquet"
        pl.DataFrame(data).write_parquet(table_path, compression="zstd")
        tables[key] = TableSpec(
            file=table_path.name,
            kind=kind,
            columns=columns,
            width=width,
            rows=len(value),
            sha256=_sha256(table_path),
        )

    manifest = BundleManifest(
        format_version=FORMAT_VERSION,
        source_sha256=_sha256(source),
        engines={
            "polars": pl.__version__,
            "pyarrow": importlib.metadata.version("pyarrow"),
        },
        scalars=scalars,
        tables=tables,
    )
    _ = (output_dir / "manifest.json").write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )


@app.command()
def unpack(bundle_dir: Path, output: Path) -> None:
    manifest = BundleManifest.model_validate_json(
        (bundle_dir / "manifest.json").read_text(encoding="utf-8")
    )
    if manifest.format_version != FORMAT_VERSION:
        raise BundleVersionError(manifest.format_version)
    payload = dict(manifest.scalars)
    for key, spec in manifest.tables.items():
        table_path = bundle_dir / spec.file
        if _sha256(table_path) != spec.sha256:
            raise ChecksumError(table_path.name)
        frame = pl.read_parquet(table_path).sort("_row")
        typed_rows: list[dict[str, object]] = []
        for raw_row_value in frame.iter_rows(named=True):
            raw_row: object = raw_row_value
            typed_rows.append(ROW_ADAPTER.validate_python(raw_row))
        if spec.kind == "dict":
            payload[key] = [
                {
                    column: _decoded(row[column])
                    for column in spec.columns
                }
                for row in typed_rows
            ]
        else:
            payload[key] = [
                [
                    _decoded(row[f"c{index:03d}"])
                    for index in range(spec.width)
                ]
                for row in typed_rows
            ]
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


if __name__ == "__main__":
    app()
