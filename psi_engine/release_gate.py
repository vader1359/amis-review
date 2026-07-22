from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .sources import REQUIRED_SOURCES


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
    required_snapshots = [row for row in snapshots if str(row.get("source_type")) in REQUIRED_SOURCES]
    missing = sorted(set(REQUIRED_SOURCES) - source_types)
    if missing:
        reasons.append(ReleaseGateReason("missing_required_source", "selected source required: " + ", ".join(missing)))
    if any(str(row.get("schema_status")) != "passed" for row in required_snapshots):
        reasons.append(ReleaseGateReason("schema_failure", "schema results are not clean"))
    for row in required_snapshots:
        try:
            age = (as_of - date.fromisoformat(str(row.get("data_as_of")))).days
        except ValueError:
            reasons.append(ReleaseGateReason("invalid_data_as_of", "source data_as_of is invalid"))
            continue
        if age < 0 or age > max_source_age_days:
            reasons.append(ReleaseGateReason("stale_source", f"selected source is stale (age {age} days; limit {max_source_age_days})"))
    active_statuses = {"new", "assigned", "in_progress", "reopened"}
    active_mismatches = [row for row in mismatches if str(row.get("status")) in active_statuses]
    if active_mismatches:
        reasons.append(ReleaseGateReason("unresolved_mismatches", f"{len(active_mismatches)} mismatch chưa được xử lý"))
    return ReleaseGateDecision(not reasons, tuple(reasons))
