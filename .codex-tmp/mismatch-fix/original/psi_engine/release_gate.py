from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Final

REQUIRED_SOURCES: Final[tuple[str, ...]] = ("product", "purchase", "revenue", "inventory", "preorder", "crm", "target")
@dataclass(frozen=True, slots=True)
class ReleaseGateReason:
    code: str
    message: str
    blocking: bool = True


@dataclass(frozen=True, slots=True)
class ReleaseGateDecision:
    allowed: bool
    reasons: tuple[ReleaseGateReason, ...]

    @property
    def messages(self) -> tuple[str, ...]:
        return tuple(reason.message for reason in self.reasons)


def evaluate_gate(
    snapshots: list[dict[str, object]],
    mismatches: list[dict[str, object]],
    as_of: date,
    max_source_age_days: int,
) -> ReleaseGateDecision:
    reasons: list[ReleaseGateReason] = []
    source_types = {str(row.get("source_type")) for row in snapshots}
    missing = sorted(set(REQUIRED_SOURCES) - source_types)
    if missing:
        reasons.append(ReleaseGateReason("missing_required_source", "selected source required: " + ", ".join(missing)))
    if any(str(row.get("schema_status")) != "passed" for row in snapshots):
        reasons.append(ReleaseGateReason("schema_failure", "schema results are not clean"))
    for row in snapshots:
        try:
            age = (as_of - date.fromisoformat(str(row.get("data_as_of")))).days
        except ValueError:
            reasons.append(ReleaseGateReason("invalid_data_as_of", "source data_as_of is invalid"))
            continue
        if age < 0 or age > max_source_age_days:
            reasons.append(ReleaseGateReason("stale_source", f"selected source is stale (age {age} days; limit {max_source_age_days})"))
    return ReleaseGateDecision(not reasons, tuple(reasons))
