# PSI full logic audit

Scope: read-only audit first; no deploy, merge, push, live migration, or source changes beyond the already-approved signed-discount fix.

1. Inventory every source, sheet, field, and formula used by the current engine.
2. Reconcile high-risk records across MISA, CRM, Pre-order feedback, and PSI output.
3. Run independent assertions for revenue filtering, returns, discounts, gifts/FOC, mapping, and period boundaries.
4. Report confirmed defects separately from data-quality exceptions and propose bounded fixes.

Milestone gate: after steps 2-3, rerun the independent assertions once and preserve evidence.
