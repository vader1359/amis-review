"""Orchestration must stop before output whenever an earlier proof fails."""

import sys
import types
from datetime import date

import pytest

from psi_tool import online_pipeline as pipeline


@pytest.fixture
def selected():
    snapshot = pipeline.SourceSnapshot.from_bytes("test.xlsx", b"PKfixture")
    return dict.fromkeys(pipeline.SOURCE_LABELS, snapshot), snapshot


def test_source_checksum_rejected_before_engine(selected):
    sources, prior = selected
    sources["crm"] = pipeline.SourceSnapshot("test.xlsx", b"PKdifferent", "0" * 64)
    with pytest.raises(pipeline.PipelineError, match="SOURCE_CHECKSUM_MISMATCH"):
        pipeline.build_draft(sources, date(2026, 9, 3), prior)


def test_baseline_and_all_sources_required(selected):
    sources, prior = selected
    with pytest.raises(pipeline.PipelineError, match="PRIOR_PSI_REQUIRED"):
        pipeline.build_draft(sources, date(2026, 9, 3), None)
    del sources["manual_check"]
    with pytest.raises(pipeline.PipelineError, match="SOURCE_SET_INVALID"):
        pipeline.build_draft(sources, date(2026, 9, 3), prior)


def test_parquet_preserves_mixed_values_and_empty_relations(tmp_path):
    payload = {
        "relation": [[None, 1, 1.25, "=1+1", False, "Tiếng Việt"]],
        "empty": [],
        "gates": [{"status": "PASS"}],
        "as_of": "2026-09-03",
    }
    assert pipeline.roundtrip_payload(payload, tmp_path) == payload


def test_nested_gate_provenance_hides_scratch_paths_without_changing_data():
    payload = {
        "gates": [{"notes": "Prior PSI: /private/run/prior.xlsx"}],
        "rows": [[12.5, "SKU-1", None]],
        "sources": {"CRM": "/private/run/crm.xlsx"},
    }
    result = pipeline._display_provenance(
        payload,
        {
            "/private/run/prior.xlsx": "PSI_Final_27.08.2026.xlsx",
            "/private/run/crm.xlsx": "CRM.xlsx",
        },
    )
    assert result["gates"][0]["notes"] == "Prior PSI: PSI_Final_27.08.2026.xlsx"
    assert result["sources"]["CRM"] == "CRM.xlsx"
    assert result["rows"] == payload["rows"]


@pytest.mark.parametrize("stage", ["payload", "parquet", "workbook"])
def test_failed_gate_never_returns_draft(selected, monkeypatch, stage):
    sources, prior = selected
    monkeypatch.setattr(pipeline, "verify_baseline", lambda *args: date(2026, 8, 27))
    calls = []
    passed = {"status": "PASS", "failure_count": 0, "failures": []}
    failed = {"status": "FAIL", "failure_count": 1, "failures": ["injected"]}
    engine = types.ModuleType("psi_tool.online_engine")
    engine.prepare_payload = lambda *args: {"as_of": "2026-09-03", "rows": []}
    engine.validate_payload = lambda *args: failed if stage == "payload" else passed
    workbook = types.ModuleType("psi_tool.online_workbook")

    def render(payload):
        calls.append("render")
        return b"xlsx"

    workbook.build_workbook = render
    workbook.validate_workbook = lambda *args: failed if stage == "workbook" else passed
    monkeypatch.setitem(sys.modules, engine.__name__, engine)
    monkeypatch.setitem(sys.modules, workbook.__name__, workbook)
    if stage == "parquet":

        def fail(*args):
            raise pipeline.PipelineError("PARQUET_PARITY_FAILED")

        monkeypatch.setattr(pipeline, "roundtrip_payload", fail)
    with pytest.raises(pipeline.PipelineError):
        pipeline.build_draft(sources, date(2026, 9, 3), prior)
    assert calls == (["render"] if stage == "workbook" else [])
