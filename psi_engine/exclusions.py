from __future__ import annotations

from typing import Any

def text(value: Any) -> str:
    return str(value or "").strip().upper()

def row_matches(row: dict[str, Any], rule: dict[str, Any]) -> bool:
    value = text(row.get(str(rule.get("match_field", ""))))
    operator = rule.get("operator")
    target = rule.get("match_value")
    if operator == "truthy":
        return value in {"TRUE", "1", "YES", "Y", "X", "LOẠI KHỎI TỒN KHO"}
    if operator == "contains":
        return text(target) in value
    values = target if isinstance(target, list) else [target]
    return value in {text(item) for item in values}

def apply_rules(source: str, rows: list[dict[str, Any]], rules: list[dict[str, Any]]):
    kept, excluded = [], []
    for row in rows:
        hit = next((rule for rule in rules if rule.get("active", True) and rule.get("source_type") in (None, source) and row_matches(row, rule)), None)
        (excluded if hit else kept).append({"row": row, "rule": hit} if hit else row)
    return kept, excluded
