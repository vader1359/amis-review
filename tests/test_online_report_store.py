"""Online persistence transactions, typed sheets and exact regenerated downloads."""

import copy
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, date, datetime

import psycopg
import pytest
from web import online_report_store as module

from psi_tool.online_pipeline import DraftResult
from psi_tool.online_workbook import build_workbook


@pytest.fixture
def draft():
    payload = {
        "as_of": "2026-09-03",
        "sources": {"Revenue": "revenue.xlsx", "CRM": "crm.xlsx"},
        "source_hashes": {"Revenue": "a" * 64, "CRM": "b" * 64},
        "gates": [{"check": "independent", "status": "PASS"}],
        "brand_rows": [["=1+1", "001"], ["Sample", "Example"]],
        "summary": {"total": 1},
    }
    content = build_workbook(payload)
    digest = hashlib.sha256(content).hexdigest()
    evidence = {
        "state": "draft",
        "input_hash": "a" * 64,
        "workbook_sha256": digest,
        "payload_sha256": module._sha(payload),
        **{
            name: {"status": "PASS", "failure_count": 0}
            for name in (
                "payload_validation",
                "parquet_validation",
                "workbook_validation",
            )
        },
    }
    return DraftResult(content, payload, evidence, "a" * 64, digest)


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return copy.deepcopy(self.rows[0]) if self.rows else None

    def fetchall(self):
        return copy.deepcopy(self.rows)


class Database:
    """Small transaction double; JSONB deliberately sorts object keys."""

    def __init__(self):
        self.reports = {}
        self.sheets = []
        self.rows = []
        self.corrupt_readback = False

    def execute(self, sql, params=()):
        if sql.startswith("INSERT INTO psi_preview.reports"):
            keys = [
                "id",
                "as_of",
                "input_hash",
                "workbook_sha256",
                "payload_sha256",
                "renderer_fingerprint",
                "snapshot_sha256",
                "payload",
                "payload_json",
                "evidence",
                "summary",
                "gates",
            ]
            value = dict(zip(keys, params, strict=True))
            for key, item in value.items():
                if isinstance(item, module.Jsonb):
                    value[key] = json.loads(module._json(item.obj))
            if any(
                r["input_hash"] == value["input_hash"]
                and r["workbook_sha256"] == value["workbook_sha256"]
                for r in self.reports.values()
            ):
                return Result([])
            value.update(
                as_of=date.fromisoformat(value["as_of"]),
                created_at=datetime.now(UTC),
                state="draft",
                sheet_count=17,
            )
            self.reports[value["id"]] = value
            return Result([{"id": value["id"]}])
        if sql.startswith("INSERT INTO psi_preview.sheets"):
            keys = [
                "report_id",
                "ordinal",
                "name",
                "row_count",
                "column_count",
                "populated_rows",
                "cell_count",
                "sha256",
            ]
            self.sheets.append(dict(zip(keys, params, strict=True)))
            return Result([])
        if "FROM psi_preview.sheet_rows" in sql:
            rows = [
                r
                for r in self.rows
                if r["report_id"] == params[0] and r["sheet_ordinal"] == params[1]
            ]
            if "LIMIT" in sql:
                rows = rows[params[3] : params[3] + params[2]]
            selected = [
                {"row_number": r["row_number"], "cells": r["cells"]} for r in rows
            ]
            if self.corrupt_readback and selected:
                selected = selected[:-1]
            return Result(selected)
        if "FROM psi_preview.sheets" in sql:
            return Result(
                [
                    {k: v for k, v in r.items() if k != "report_id"}
                    for r in self.sheets
                    if r["report_id"] == params[0]
                ]
            )
        if "FROM psi_preview.reports" in sql:
            rows = list(self.reports.values())
            if "WHERE input_hash=" in sql:
                rows = [
                    r
                    for r in rows
                    if r["input_hash"] == params[0]
                    and r["workbook_sha256"] == params[1]
                ]
            elif "WHERE id=" in sql:
                rows = [r for r in rows if r["id"] == params[0]]
            if "LIMIT" in sql:
                rows = rows[params[1] : params[1] + params[0]]
            fields = sql.partition("SELECT ")[2].partition(" FROM")[0].split(", ")
            return Result([{key: row[key] for key in fields} for row in rows])
        raise AssertionError(sql)

    def cursor(self):
        return self

    @contextmanager
    def copy(self, sql):
        assert sql.startswith("COPY psi_preview.sheet_rows")
        yield self

    def write_row(self, row):
        report_id, ordinal, number, cells = row
        self.rows.append(
            {
                "report_id": report_id,
                "sheet_ordinal": ordinal,
                "row_number": number,
                "cells": json.loads(cells),
            }
        )


@pytest.fixture
def storage(monkeypatch):
    database = Database()

    @contextmanager
    def connect():
        previous = copy.deepcopy((database.reports, database.sheets, database.rows))
        try:
            yield database
        except Exception:
            database.reports, database.sheets, database.rows = previous
            raise

    store = module.OnlineReportStore(
        "postgresql://user:secret@ep-test.neon.tech/neondb"
    )
    monkeypatch.setattr(store, "_connect", connect)
    return store, database


def test_atomic_save_exact_rebuild_and_idempotence(storage, draft):
    store, database = storage
    saved = store.save(draft)
    assert saved["storage"] == "neon"
    assert saved["state"] == "draft"
    assert saved["sheet_count"] == 17
    assert saved == store.save(draft)
    assert len(database.reports) == 1
    assert store.get(saved["id"]) == saved
    assert store.list() == [saved]
    assert len(store.sheets(saved["id"])) == 17
    assert store.download(saved["id"]) == draft.xlsx
    assert list(database.reports[saved["id"]]["payload"]["sources"]) == [
        "CRM",
        "Revenue",
    ]
    assert (
        json.loads(database.reports[saved["id"]]["payload_json"])["sources"]
        == draft.payload["sources"]
    )


def test_save_reuses_outer_transaction_and_rolls_back_on_later_failure(storage, draft, monkeypatch):
    store, database = storage
    outer_connect = store._connect
    monkeypatch.setattr(store, "_connect", lambda: pytest.fail("opened nested transaction"))
    with pytest.raises(RuntimeError, match="audit failed"):
        with outer_connect() as connection:
            saved = store.save(draft, connection=connection)
            assert saved["id"] in database.reports
            assert database.sheets and database.rows
            raise RuntimeError("audit failed")
    assert not database.reports
    assert not database.sheets
    assert not database.rows


def test_save_with_supplied_connection_retains_success_for_outer_commit(storage, draft, monkeypatch):
    store, database = storage
    outer_connect = store._connect
    monkeypatch.setattr(store, "_connect", lambda: pytest.fail("opened nested transaction"))
    with outer_connect() as connection:
        saved = store.save(draft, connection=connection)
    assert saved["id"] in database.reports


def test_snapshot_preserves_formulas_cache_and_formula_like_text(draft):
    snapshots = module.snapshot_workbook(draft.xlsx)
    summary = snapshots[0]
    formula = next(
        c for r in summary["rows"] for c in r["cells"] if c["type"] == "formula"
    )
    assert formula["formula"].startswith("=SUM(")
    assert formula["cached_type"] == "number"
    assert formula["cached_value"] == 0
    brand = next(s for s in snapshots if s["name"] == "Brand")
    row = next(r for r in brand["rows"] if r["row_number"] == 4)
    assert row["cells"][0] == {"column": 1, "type": "text", "value": "=1+1"}
    assert row["cells"][1]["value"] == "001"


def test_partial_readback_rolls_back_every_table(storage, draft):
    store, database = storage
    database.corrupt_readback = True
    with pytest.raises(module.ReportStoreError, match="ONLINE_REPORT_INTEGRITY_FAILED"):
        store.save(draft)
    assert not database.reports and not database.sheets and not database.rows


def test_conflicting_evidence_does_not_overwrite(storage, draft):
    store, database = storage
    saved = store.save(draft)
    changed = replace(draft, evidence={**draft.evidence, "unexpected": True})
    with pytest.raises(module.ReportStoreError, match="ONLINE_REPORT_INTEGRITY_FAILED"):
        store.save(changed)
    assert "unexpected" not in database.reports[saved["id"]]["evidence"]


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("payload_sha256", "0" * 64, "ONLINE_REPORT_INTEGRITY_FAILED"),
        ("renderer_fingerprint", "other", "ONLINE_REPORT_VERSION_UNSUPPORTED"),
        ("workbook_sha256", "0" * 64, "ONLINE_REPORT_INTEGRITY_FAILED"),
        ("snapshot_sha256", "0" * 64, "ONLINE_REPORT_INTEGRITY_FAILED"),
    ],
)
def test_download_refuses_tampered_snapshot(storage, draft, field, value, code):
    store, database = storage
    saved = store.save(draft)
    database.reports[saved["id"]][field] = value
    with pytest.raises(module.ReportStoreError, match=code):
        store.download(saved["id"])


def test_failed_validation_cannot_be_saved(storage, draft):
    store, database = storage
    with pytest.raises(module.ReportStoreError, match="REPORT_VALIDATION_REQUIRED"):
        store.save(replace(draft, xlsx=draft.xlsx + b"tampered"))
    assert not database.reports


def test_pages_are_bounded_and_missing_download_is_explicit(storage):
    store, _ = storage
    with pytest.raises(module.ReportStoreError, match="REPORT_PAGE_INVALID"):
        store.list(limit=101)
    with pytest.raises(module.ReportStoreError, match="REPORT_PAGE_INVALID"):
        store.sheet_rows("a" * 32, 1, offset=-1)
    with pytest.raises(module.ReportStoreError, match="REPORT_SHEET_INVALID"):
        store.sheet_rows("a" * 32, 18)
    with pytest.raises(module.ReportStoreError, match="ONLINE_REPORT_NOT_FOUND"):
        store.download("a" * 32)
    with pytest.raises(module.ReportStoreError, match="ONLINE_REPORT_NOT_FOUND"):
        store.sheets("a" * 32)
    with pytest.raises(module.ReportStoreError, match="ONLINE_REPORT_NOT_FOUND"):
        store.sheet_rows("a" * 32, 1)


def test_driver_error_is_sanitized(monkeypatch):
    def fail(*args, **kwargs):
        raise psycopg.OperationalError("secret password and private server details")

    monkeypatch.setattr(module.psycopg, "connect", fail)
    store = module.OnlineReportStore(
        "postgresql://user:secret@ep-test.neon.tech/neondb"
    )
    with pytest.raises(module.ReportStoreError, match="^ONLINE_STORAGE_UNAVAILABLE$"):
        store.list()


def test_missing_and_wrong_provider_config_refused():
    for value in (
        "",
        "postgresql://localhost/database",
        "https://ep-test.neon.tech/db",
    ):
        with pytest.raises(
            module.ReportStoreError, match="ONLINE_DATABASE_CONFIG_INVALID"
        ):
            module.OnlineReportStore(value)


def test_cached_original_download_survives_renderer_change(storage, draft, tmp_path, monkeypatch):
    store, database = storage
    store._artifact_dir = tmp_path / "artifacts"
    saved = store.save(draft)
    artifact = store._artifact_dir / f"{draft.workbook_sha256}.xlsx"
    assert artifact.read_bytes() == draft.xlsx
    assert artifact.stat().st_mode & 0o777 == 0o600
    assert store._artifact_dir.stat().st_mode & 0o777 == 0o700
    assert store.save(draft) == saved
    assert len(list(store._artifact_dir.iterdir())) == 1
    monkeypatch.setattr(module, "renderer_fingerprint", lambda: "new-platform")
    monkeypatch.setattr(module.online_workbook, "build_workbook", lambda _: pytest.fail("regenerated"))
    assert store.download(saved["id"]) == draft.xlsx
    database.reports[saved["id"]]["snapshot_sha256"] = "0" * 64
    with pytest.raises(module.ReportStoreError, match="ONLINE_REPORT_INTEGRITY_FAILED"):
        store.download(saved["id"])


def test_corrupt_cache_fails_closed_for_save_and_download(storage, draft, tmp_path):
    store, _ = storage
    store._artifact_dir = tmp_path / "artifacts"
    saved = store.save(draft)
    artifact = store._artifact_dir / f"{draft.workbook_sha256}.xlsx"
    artifact.write_bytes(b"corrupted")
    for action in (lambda: store.download(saved["id"]), lambda: store.save(draft)):
        with pytest.raises(module.ReportStoreError, match="ONLINE_REPORT_INTEGRITY_FAILED"):
            action()
    assert artifact.read_bytes() == b"corrupted"


def test_missing_cache_only_rebuilds_matching_renderer(storage, draft, tmp_path, monkeypatch):
    store, _ = storage
    saved = store.save(draft)
    store._artifact_dir = tmp_path / "artifacts"
    original = module.renderer_fingerprint
    monkeypatch.setattr(module, "renderer_fingerprint", lambda: "other")
    with pytest.raises(module.ReportStoreError, match="ONLINE_REPORT_VERSION_UNSUPPORTED"):
        store.download(saved["id"])
    monkeypatch.setattr(module, "renderer_fingerprint", original)
    assert store.download(saved["id"]) == draft.xlsx
    assert (store._artifact_dir / f"{draft.workbook_sha256}.xlsx").read_bytes() == draft.xlsx


def test_artifact_configuration_explicit_and_environment(tmp_path, monkeypatch):
    dsn = "postgresql://user:secret@ep-test.neon.tech/neondb"
    monkeypatch.setenv("PSI_REPORT_ARTIFACT_DIR", str(tmp_path / "environment"))
    assert module.OnlineReportStore(dsn)._artifact_dir == tmp_path / "environment"
    assert module.OnlineReportStore(dsn, tmp_path / "explicit")._artifact_dir == tmp_path / "explicit"


@pytest.mark.parametrize("target", ["directory", "ancestor", "file", "traversal"])
def test_cache_symlink_and_path_safety(storage, draft, tmp_path, target):
    store, database = storage
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    link = tmp_path / "linked"
    link.symlink_to(real, target_is_directory=True)
    store._artifact_dir = {
        "directory": link,
        "ancestor": link / "child",
        "file": real,
        "traversal": real / ".." / "escape",
    }[target]
    victim = tmp_path / "victim.xlsx"
    victim.write_bytes(draft.xlsx)
    victim.chmod(0o600)
    if target == "file":
        (real / f"{draft.workbook_sha256}.xlsx").symlink_to(victim)
    with pytest.raises(module.ReportStoreError):
        store.save(draft)
    assert not database.reports
    assert victim.read_bytes() == draft.xlsx
    assert not (tmp_path / "escape").exists()


def test_cache_write_failure_is_atomic_and_prevents_db_success(storage, draft, tmp_path, monkeypatch):
    store, database = storage
    store._artifact_dir = tmp_path / "artifacts"

    def fail_sync(_):
        raise OSError("private filesystem failure")

    monkeypatch.setattr(module.os, "fsync", fail_sync)
    with pytest.raises(module.ReportStoreError, match="^REPORT_ARTIFACT_UNAVAILABLE$"):
        store.save(draft)
    assert not database.reports
    assert list(store._artifact_dir.iterdir()) == []


def test_cache_size_and_private_permissions_are_enforced(storage, draft, tmp_path, monkeypatch):
    store, database = storage
    store._artifact_dir = tmp_path / "artifacts"
    monkeypatch.setattr(module, "MAX_ARTIFACT_BYTES", len(draft.xlsx) - 1)
    with pytest.raises(module.ReportStoreError, match="REPORT_SIZE_INVALID"):
        store.save(draft)
    assert not database.reports
    monkeypatch.setattr(module, "MAX_ARTIFACT_BYTES", len(draft.xlsx))
    saved = store.save(draft)
    artifact = store._artifact_dir / f"{draft.workbook_sha256}.xlsx"
    os.chmod(artifact, 0o644)
    with pytest.raises(module.ReportStoreError, match="ONLINE_REPORT_INTEGRITY_FAILED"):
        store.download(saved["id"])


def test_concurrent_cache_publication_keeps_one_complete_original(storage, draft, tmp_path):
    store, _ = storage
    store._artifact_dir = tmp_path / "artifacts"
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(store._cache_artifact, draft.xlsx, draft.workbook_sha256)
            for _ in range(8)
        ]
        for future in futures:
            future.result()
    files = list(store._artifact_dir.iterdir())
    assert len(files) == 1
    assert files[0].read_bytes() == draft.xlsx
    original_inode = files[0].stat().st_ino
    store._cache_artifact(draft.xlsx, draft.workbook_sha256)
    assert files[0].stat().st_ino == original_inode
