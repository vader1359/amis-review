import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))
import server  # noqa: E402
from psi_engine import PsiReleaseService, ReleaseConfig, ReleaseGateError, ReleaseRequest, evaluate_gate
from psi_engine.release_gate import REQUIRED_SOURCES

FIXTURES = Path(__file__).parent / "fixtures"


def release_store() -> server.PsiMemoryStore:
    store = server.PsiMemoryStore()
    sources = (("product", "product_fixture.xlsx"), ("purchase", "loading_purchase_fixture.xlsx"), ("revenue", "so_chi_tiet_revenue_fixture.xlsx"), ("inventory", "tong_hop_ton_kho_inventory_fixture.xlsx"), ("preorder", "pre-order_fixture.xlsx"), ("crm", "crm_sale_fixture.xlsx"), ("target", "target_fixture.xlsx"))
    for source_type, filename in sources:
        store.persist(server.UploadRequest("team-a", "user-a", "2026-07", "2026-07-05", source_type, filename, (FIXTURES / filename).read_bytes()))
    return store


def test_release_generates_immutable_openable_final_with_checksum() -> None:
    store = release_store()
    record = PsiReleaseService(store).generate(ReleaseRequest("2026-07", "user-a"))
    assert record.status == "published"
    assert record.object_path.endswith("/PSI Final.xlsx")
    assert record.checksum_sha256
    with pytest.raises(server.UploadValidationError):
        store.repository.upload(record.object_path, b"replacement")


def test_release_gates_missing_stale_tampered_and_blocking_inputs() -> None:
    store = release_store()
    store.snapshots = [snapshot for snapshot in store.snapshots if snapshot.source_type != "target"]
    with pytest.raises(ReleaseGateError, match="selected source required: target"):
        PsiReleaseService(store).generate(ReleaseRequest("2026-07", "user-a"))
    store = release_store()
    with pytest.raises(ReleaseGateError, match="stale"):
        PsiReleaseService(store, ReleaseConfig(max_source_age_days=1, as_of=date(2026, 7, 14))).generate(ReleaseRequest("2026-07", "user-a"))
    selected = store.selections["2026-07", "product"]
    source_path = next(snapshot.object_path for snapshot in store.snapshots if snapshot.id == selected)
    store.repository.objects[source_path] = b"tampered"
    with pytest.raises(ReleaseGateError, match="checksum"):
        PsiReleaseService(store).generate(ReleaseRequest("2026-07", "user-a"))


def test_release_gate_rejects_corrupt_generated_workbook_before_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    store = release_store()
    monkeypatch.setattr("psi_engine.release.build", lambda files: SimpleNamespace(summary={}, issues=[], gaps=[], xlsx=b"not-an-xlsx"))
    with pytest.raises(ReleaseGateError, match="not openable"):
        PsiReleaseService(store).generate(ReleaseRequest("2026-07", "user-a"))
    assert not any("PSI Draft.xlsx" in path or "PSI Final.xlsx" in path for path in store.repository.objects)


@pytest.mark.parametrize(
    ("severity", "status"),
    [
        ("blocking", "new"),
        ("blocking", "assigned"),
        ("warning", "in_progress"),
        ("info", "reopened"),
        ("blocking", "resolved"),
    ],
)
def test_release_gate_reports_mismatches_without_blocking_generation(severity: str, status: str) -> None:
    snapshots = [{"source_type": source, "schema_status": "passed", "data_as_of": "2026-07-05"} for source in REQUIRED_SOURCES]
    decision = evaluate_gate(snapshots, [{"severity": severity, "status": status}], date(2026, 7, 5), 30)
    assert decision.allowed
    assert not decision.reasons


def test_release_generates_final_when_reconciliation_has_new_mismatch() -> None:
    store = release_store()
    store.repository.insert(
        "mismatches",
        {"reporting_period_id": "2026-07", "severity": "blocking", "status": "new"},
    )
    record = PsiReleaseService(store).generate(ReleaseRequest("2026-07", "user-a"))
    assert record.status == "published"


@pytest.mark.parametrize("failed_table", ["psi_drafts", "draft_sources", "psi_releases", "release_sources", "activity_logs"])
def test_release_compensates_every_post_upload_metadata_failure(failed_table: str) -> None:
    store = release_store()
    previous = PsiReleaseService(store).generate(ReleaseRequest("2026-07", "user-a"))
    original_insert = store.repository.insert

    def failing_insert(table: str, row: dict[str, object], auth_token: str = "") -> None:
        if table == failed_table:
            raise server.UploadValidationError("metadata write failed")
        original_insert(table, row, auth_token)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(store.repository, "insert", failing_insert)
    baseline_runs = {str(row["id"]) for row in store.repository.rows("reconciliation_runs")}
    baseline_run_sources = len(store.repository.rows("reconciliation_run_sources"))
    baseline_drafts = len(store.repository.rows("psi_drafts"))
    baseline_draft_sources = len(store.repository.rows("draft_sources"))
    baseline_releases = len(store.repository.rows("psi_releases"))
    baseline_release_sources = len(store.repository.rows("release_sources"))
    baseline_activity = len(store.repository.rows("activity_logs"))
    baseline_objects = set(store.repository.objects)
    with pytest.raises(server.UploadValidationError, match="metadata write failed"):
        PsiReleaseService(store).generate(ReleaseRequest("2026-07", "user-a"))
    assert set(store.repository.objects) == baseline_objects
    assert store.repository.lookup("psi_releases", {"id": previous.id})
    assert {str(row["id"]) for row in store.repository.rows("reconciliation_runs")} == baseline_runs
    assert len(store.repository.rows("reconciliation_run_sources")) == baseline_run_sources
    assert len(store.repository.rows("psi_drafts")) == baseline_drafts
    assert len(store.repository.rows("draft_sources")) == baseline_draft_sources
    assert len(store.repository.rows("psi_releases")) == baseline_releases
    assert len(store.repository.rows("release_sources")) == baseline_release_sources
    assert len(store.repository.rows("activity_logs")) == baseline_activity
    assert store.repository.lookup("psi_releases", {"id": previous.id})
