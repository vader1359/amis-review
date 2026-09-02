from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from .manual_check import ManualCheckRegistry, load_manual_check, partition_mismatches

def fingerprint(source_type: str, record_key: str, issue_type: str, values_by_source: dict[str, Any]) -> str:
    material = json.dumps(values_by_source, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{source_type}|{record_key}|{issue_type}|{material}".encode()).hexdigest()

def cases_from_engine_issues(issues: list[list[Any]]) -> list[dict[str, Any]]:
    cases = []
    for source, code, description, issue in issues:
        key = str(code or "")  # Raw SKU/code remains exact: never normalize or fall back to name.
        values = {"description": description or ""}
        cases.append({"fingerprint": fingerprint(str(source), key, str(issue), values), "record_key": key,
                      "source_type": str(source), "issue_type": str(issue), "severity": "warning",
                      "values_by_source": values})
    return cases


def reconcile_with_manual_check(
    issues: list[list[Any]],
    manual_check: ManualCheckRegistry | str | Path | bytes,
    as_of: date | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep new/unapproved cases active and suppress only exact approved matches."""

    registry = manual_check if isinstance(manual_check, ManualCheckRegistry) else load_manual_check(manual_check)
    return partition_mismatches(cases_from_engine_issues(issues), registry, as_of)
