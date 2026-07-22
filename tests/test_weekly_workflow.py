import io
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))
import server  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
SOURCES = {
    "product": "product_fixture.xlsx",
    "purchase": "loading_purchase_fixture.xlsx",
    "revenue": "so_chi_tiet_revenue_fixture.xlsx",
    "inventory": "tong_hop_ton_kho_inventory_fixture.xlsx",
    "preorder": "pre-order_fixture.xlsx",
    "crm": "crm_sale_fixture.xlsx",
    "target": "target_fixture.xlsx",
}


def request(source: str, week: str = "2026-W29") -> server.UploadRequest:
    return server.UploadRequest(
        team_id="team-a", actor_id="anonymous-uploader", reporting_period=week,
        data_as_of="", source_type=source, filename=SOURCES[source],
        content=(FIXTURES / SOURCES[source]).read_bytes(),
    )


def test_anonymous_weekly_upload_tracks_latest_versions_and_missing_readiness() -> None:
    store = server.PsiMemoryStore()
    first = store.persist(request("product"))
    assert first.snapshot.version == 1
    assert store.weekly_status("team-a", "2026-W29")["ready"] is False
    second = store.persist(request("product"))
    status = store.weekly_status("team-a", "2026-W29")
    assert second.snapshot.version == 2
    assert status["files"]["product"]["version"] == 2
    assert len(store.snapshots) == 2
    assert status["files"]["revenue"]["status"] == "missing"


def test_weekly_status_is_team_scoped() -> None:
    store = server.PsiMemoryStore()
    store.persist(request("product"))
    assert store.weekly_status("team-b", "2026-W29")["files"]["product"]["status"] == "missing"


def test_invalid_iso_week_is_rejected() -> None:
    with pytest.raises(server.UploadValidationError):
        server.week_to_period("2026-07")


def test_weekly_release_generates_openable_workbook() -> None:
    store = server.PsiMemoryStore()
    for source in SOURCES:
        store.persist(request(source))
    record = server.PsiReleaseService(store).generate(server.ReleaseRequest("2026-W29", "anonymous-uploader", "team-a"))
    token = record.signed_url.rsplit("/", 1)[1] if record.signed_url else ""
    load_workbook(io.BytesIO(server.PsiReleaseService(store).local_download(token, "anonymous-uploader"))).close()


def test_weekly_status_exposes_download_after_all_sources() -> None:
    store = server.PsiMemoryStore()
    for source in SOURCES:
        store.persist(request(source))
    status = store.weekly_status("team-a", "2026-W29")
    assert status["ready"] is True
    assert status["download_url"]


def test_weekly_release_does_not_cross_team_versions() -> None:
    store = server.PsiMemoryStore()
    for source in SOURCES:
        store.persist(request(source))
        store.persist(server.UploadRequest(
            team_id="team-b", actor_id="anonymous-uploader", reporting_period="2026-W29",
            data_as_of="", source_type=source, filename=SOURCES[source],
            content=(FIXTURES / SOURCES[source]).read_bytes(),
        ))
    status = store.weekly_status("team-b", "2026-W29")
    assert status["ready"] is True
    assert status["files"]["product"]["version"] == 1


def test_weekly_release_is_team_scoped() -> None:
    store = server.PsiMemoryStore()
    for source in SOURCES:
        store.persist(request(source))
    with pytest.raises(server.ReleaseGateError):
        server.PsiReleaseService(store).generate(server.ReleaseRequest("2026-W29", "anonymous-uploader", "team-b"))
