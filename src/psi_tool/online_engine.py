"""Portable, deterministic PSI preparation and independent release validation.

Every input is explicit. Neither entry point searches the checkout, writes files,
or retains run state, so independent jobs may safely run concurrently.
"""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from ._online_prepare import prepare, sha256_file
from ._online_validate import validate

SOURCE_LABELS = (
    "CRM Sales Order",
    "Product Master",
    "Revenue",
    "Inventory",
    "Purchase/PO",
    "Target",
    "Manual Check",
)
RELATION_WIDTHS = (
    ("revenue_rows", 18),
    ("inventory_rows", 11),
    ("purchase_rows", 15),
    ("po_excluded_rows", 4),
    ("preorder_rows", 18),
    ("preorder_excluded_rows", 18),
    ("psi_product_rows", 15),
    ("crm_final_rows", 10),
    ("crm_product_rows", 6),
    ("brand_rows", 2),
    ("category_rows", 2),
    ("target_rows", None),
    ("mismatch_rows", 6),
    ("new_mismatch_keys", 3),
    ("data_gap_rows", 4),
    ("data_gaps_rows", 4),
)


def _inputs(sources: dict[str, Path], as_of: date, prior_psi: Path) -> dict[str, Path]:
    if not isinstance(as_of, date) or isinstance(as_of, datetime):
        raise ValueError("as_of must be a calendar date")
    if as_of < date(2024, 1, 1):
        raise ValueError("as_of precedes the supported PSI period")
    if not isinstance(sources, dict) or set(sources) != set(SOURCE_LABELS):
        raise ValueError("Exactly the seven official source labels are required")
    normalized = {name: Path(sources[name]) for name in SOURCE_LABELS}
    if prior_psi is None:
        raise ValueError("An explicit prior PSI baseline is required")
    for name, path in (*normalized.items(), ("Prior PSI", Path(prior_psi))):
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing or empty {name} workbook: {path}")
    return normalized


def _check_json(value: Any) -> None:
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("Payload contains a non-finite number")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("Payload object keys must be strings")
            _check_json(item)
    elif isinstance(value, list):
        for item in value:
            _check_json(item)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValueError("Payload contains a non-JSON value")


def _fingerprints(sources: dict[str, Path], prior_psi: Path) -> dict[str, str]:
    return {
        name: sha256_file(path)
        for name, path in (*sources.items(), ("Prior PSI", prior_psi))
    }


def prepare_payload(
    sources: dict[str, Path], as_of: date, prior_psi: Path
) -> dict[str, Any]:
    """Build all 17 payload relations using the verified offline business rules."""
    sources = _inputs(sources, as_of, prior_psi)
    prior_psi = Path(prior_psi)
    before = _fingerprints(sources, prior_psi)
    payload = prepare(sources, as_of, prior_psi)
    if _fingerprints(sources, prior_psi) != before:
        raise ValueError("Input workbooks changed while preparing PSI")
    return payload


def validate_payload(
    payload: dict[str, Any], sources: dict[str, Path], as_of: date, prior_psi: Path
) -> dict[str, Any]:
    """Recompute source balances independently and return PASS or FAIL evidence."""
    try:
        sources = _inputs(sources, as_of, prior_psi)
        prior_psi = Path(prior_psi)
        if not isinstance(payload, dict):
            raise ValueError("PSI payload must be an object")
        _check_json(payload)
        for key, width in RELATION_WIDTHS:
            rows = payload.get(key)
            if not isinstance(rows, list):
                raise ValueError(f"payload {key} is not a list")
            for row in rows:
                if not isinstance(row, list) or (
                    width is not None and len(row) != width
                ):
                    raise ValueError(f"payload {key} contains an invalid row shape")
        gates = payload.get("gates")
        if (
            not isinstance(gates, list)
            or not gates
            or any(not isinstance(g, dict) for g in gates)
        ):
            raise ValueError("payload gates must contain release check objects")
        before = _fingerprints(sources, prior_psi)
        result = validate(payload, sources, as_of, prior_psi)
        if _fingerprints(sources, prior_psi) != before:
            result["failures"].append("Input workbooks changed while validating PSI")
        result["failure_count"] = len(result["failures"])
        result["result"] = result["status"] = "FAIL" if result["failures"] else "PASS"
        return result
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        OSError,
        RuntimeError,
        BadZipFile,
        ParseError,
    ) as exc:
        return {
            "status": "FAIL",
            "result": "FAIL",
            "failure_count": 1,
            "failures": [str(exc)],
            "checks": {},
            "warnings": [],
        }
