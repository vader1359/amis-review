"""Run the governed PSI build against an explicit immutable input selection.

This boundary is shared by an HTTP adapter and a job worker. Storage, identity,
approval, and publication belong to those adapters; this module produces Drafts.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .online_baseline import verify_baseline

SOURCE_LABELS = {
    "crm": "CRM Sales Order",
    "product": "Product Master",
    "revenue": "Revenue",
    "inventory": "Inventory",
    "purchase": "Purchase/PO",
    "target": "Target",
    "manual_check": "Manual Check",
}
PIPELINE_VERSION = "psi-online-parity-v2-po-column-mapping"
MAX_SOURCE_BYTES = 50 * 1024 * 1024


class PipelineError(ValueError):
    """A failed validation stage; details must remain in private run evidence."""

    def __init__(self, code: str, evidence: dict[str, Any] | None = None):
        super().__init__(code)
        self.code = code
        self.evidence = evidence or {}


@dataclass(frozen=True)
class SourceSnapshot:
    """A selected version's bytes, verified independently from its name."""

    filename: str
    content: bytes
    sha256: str

    @classmethod
    def from_bytes(cls, filename: str, content: bytes) -> SourceSnapshot:
        return cls(filename, content, hashlib.sha256(content).hexdigest())


@dataclass(frozen=True)
class DraftResult:
    """Validated Draft bytes and evidence; never implies publication approval."""

    xlsx: bytes
    payload: dict[str, Any]
    evidence: dict[str, Any]
    input_hash: str
    workbook_sha256: str


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _display_provenance(value: Any, names: dict[str, str]) -> Any:
    """Replace generated private paths with selected names in nested evidence."""
    if isinstance(value, str):
        for path, filename in names.items():
            value = value.replace(path, filename)
        return value
    if isinstance(value, list):
        return [_display_provenance(item, names) for item in value]
    if isinstance(value, dict):
        return {key: _display_provenance(item, names) for key, item in value.items()}
    return value


def _check_snapshot(snapshot: SourceSnapshot) -> None:
    if not isinstance(snapshot.content, bytes):
        raise PipelineError("SOURCE_BYTES_REQUIRED")
    if not 0 < len(snapshot.content) <= MAX_SOURCE_BYTES:
        raise PipelineError("SOURCE_SIZE_INVALID")
    if hashlib.sha256(snapshot.content).hexdigest() != snapshot.sha256:
        raise PipelineError("SOURCE_CHECKSUM_MISMATCH")
    if not snapshot.filename.lower().endswith(".xlsx"):
        raise PipelineError("SOURCE_EXTENSION_INVALID")
    if not snapshot.content.startswith(b"PK"):
        raise PipelineError("SOURCE_PACKAGE_INVALID")


def roundtrip_payload(payload: dict[str, Any], directory: Path) -> dict[str, Any]:
    """Check every relation through Parquet, preserving JSON types and order.

    A JSON cell representation deliberately retains mixed spreadsheet values.
    Files are named by ordinal, so source-controlled keys never become paths.
    """
    restored: dict[str, Any] = {}
    for ordinal, (key, value) in enumerate(payload.items()):
        if not isinstance(value, list):
            restored[key] = json.loads(_json_bytes(value))
            continue
        encoded = [_json_bytes(row).decode() for row in value]
        table = pa.table({"row_json": pa.array(encoded, type=pa.string())})
        path = directory / f"relation-{ordinal:03d}.parquet"
        pq.write_table(table, path, compression="zstd")
        restored[key] = [
            json.loads(item)
            for item in pq.read_table(path).column("row_json").to_pylist()
        ]
    if _json_bytes(restored) != _json_bytes(payload):
        raise PipelineError("PARQUET_PARITY_FAILED")
    return restored


def build_draft(
    snapshots: dict[str, SourceSnapshot],
    as_of: date,
    prior_psi: SourceSnapshot,
) -> DraftResult:
    """Validate source selection, recompute rules, and verify an exact Draft."""
    if set(snapshots) != set(SOURCE_LABELS):
        raise PipelineError("SOURCE_SET_INVALID")
    if type(as_of) is not date or as_of < date(2024, 1, 1):
        raise PipelineError("CUTOFF_INVALID")
    if not isinstance(prior_psi, SourceSnapshot):
        raise PipelineError("PRIOR_PSI_REQUIRED")
    selected = dict(snapshots)
    for snapshot in [*selected.values(), prior_psi]:
        _check_snapshot(snapshot)
    try:
        prior_date = verify_baseline(prior_psi.content, prior_psi.filename, as_of)
    except ValueError as exc:
        raise PipelineError(str(exc)) from exc
    material = {
        "version": PIPELINE_VERSION,
        "as_of": as_of.isoformat(),
        "sources": {key: selected[key].sha256 for key in SOURCE_LABELS},
        "prior_psi_sha256": prior_psi.sha256,
        "prior_as_of": prior_date.isoformat(),
        "source_filenames": {
            key: Path(selected[key].filename).name for key in SOURCE_LABELS
        },
        "prior_filename": Path(prior_psi.filename).name,
        "baseline_authority": "operator_selected_offline_final",
    }
    input_hash = hashlib.sha256(_json_bytes(material)).hexdigest()
    # Import at execution time: health/configuration inspection does not run builds.
    from .online_engine import prepare_payload, validate_payload
    from .online_workbook import build_workbook, validate_workbook

    with tempfile.TemporaryDirectory(prefix="psi-draft-") as directory:
        root = Path(directory)
        sources = {}
        for key, label in SOURCE_LABELS.items():
            source = root / f"{key}.xlsx"
            source.write_bytes(selected[key].content)
            sources[label] = source
        baseline = root / "prior.xlsx"
        baseline.write_bytes(prior_psi.content)
        payload = prepare_payload(sources, as_of, baseline)
        validation = validate_payload(payload, sources, as_of, baseline)
        if validation.get("status") != "PASS" or validation.get("failure_count") != 0:
            raise PipelineError("INDEPENDENT_VALIDATION_FAILED", validation)
        payload = roundtrip_payload(payload, root)
        # Replace private scratch paths only after independent source verification.
        display_names = {
            str(sources[SOURCE_LABELS[key]]): Path(selected[key].filename).name
            for key in SOURCE_LABELS
        }
        display_names[str(baseline)] = Path(prior_psi.filename).name
        payload = _display_provenance(payload, display_names)
        validation = _display_provenance(validation, display_names)
        payload["sources"] = {
            SOURCE_LABELS[key]: Path(selected[key].filename).name
            for key in SOURCE_LABELS
        }
        payload["prior_psi_final"] = Path(prior_psi.filename).name
        content = build_workbook(payload)
        workbook_validation = validate_workbook(content, payload)
        if (
            workbook_validation.get("status") != "PASS"
            or workbook_validation.get("failure_count") != 0
        ):
            raise PipelineError("WORKBOOK_VALIDATION_FAILED", workbook_validation)
    checksum = hashlib.sha256(content).hexdigest()
    evidence = {
        **material,
        "input_hash": input_hash,
        "state": "draft",
        "payload_validation": validation,
        "parquet_validation": {"status": "PASS", "semantic_equality": True},
        "workbook_validation": workbook_validation,
        "workbook_sha256": checksum,
        "payload_sha256": hashlib.sha256(_json_bytes(payload)).hexdigest(),
    }
    return DraftResult(content, payload, evidence, input_hash, checksum)
