"""Online report HTTP contract: persistence, failure honesty and isolation."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from web import preview
from web.online_report_store import ReportStoreError

from tests.psi_tool.test_online_preview import all_files


class FakeReports:
    def __init__(self):
        self.items = {}
        self.failed = False

    def save(self, result):
        if self.failed:
            raise ReportStoreError("ONLINE_STORAGE_UNAVAILABLE")
        item = {
            "id": "a" * 32,
            "storage": "neon",
            "state": "draft",
            "sheet_count": 17,
            "download_url": "/api/drafts/" + "a" * 32 + "/download",
        }
        self.items[item["id"]] = item
        return item

    def list(self, limit=20, offset=0):
        if self.failed:
            raise ReportStoreError("ONLINE_STORAGE_UNAVAILABLE")
        return list(self.items.values())[offset : offset + limit]

    def get(self, report_id):
        return self.items.get(report_id)

    def download(self, report_id):
        if report_id not in self.items:
            raise ReportStoreError("ONLINE_REPORT_NOT_FOUND")
        return b"persisted-verified-draft"

    def sheets(self, report_id):
        if report_id not in self.items:
            raise ReportStoreError("ONLINE_REPORT_NOT_FOUND")
        return [{"ordinal": 1, "name": "Checks"}]

    def sheet_rows(self, report_id, ordinal, limit=100, offset=0):
        return [{"row_number": 1, "cells": [{"column": 1, "value": "PASS"}]}]


def send(app, method, path, **kwargs):
    async def run():
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 12345))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://localhost"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(run())


def generate(app):
    token = send(app, "GET", "/api/config").json()["preview_token"]
    return send(
        app,
        "POST",
        "/api/drafts",
        files=all_files(),
        data={"as_of": "2026-09-03"},
        headers={"X-PSI-Preview": token},
    )


@pytest.fixture
def built(monkeypatch):
    monkeypatch.setattr(
        preview, "build_draft", lambda *args: SimpleNamespace(xlsx=b"draft")
    )


def test_online_commit_then_history_and_download_after_app_restart(tmp_path, built):
    reports = FakeReports()
    app = preview.create_app(tmp_path, report_store=reports)
    assert send(app, "GET", "/api/config").json()["report_storage"] == {
        "enabled": True,
        "provider": "neon",
    }
    response = generate(app)
    assert response.status_code == 200
    result = response.json()
    assert result["storage"] == "neon"
    restarted = preview.create_app(tmp_path, report_store=reports)
    assert (
        send(restarted, "GET", "/api/reports").json()["reports"][0]["id"]
        == result["id"]
    )
    assert (
        send(restarted, "GET", result["download_url"]).content
        == b"persisted-verified-draft"
    )
    assert (
        send(restarted, "GET", "/api/reports/" + result["id"]).json()["state"]
        == "draft"
    )
    assert send(restarted, "GET", "/api/reports/" + result["id"] + "/sheets").json()[
        "sheets"
    ]
    assert send(
        restarted, "GET", "/api/reports/" + result["id"] + "/sheets/1/rows"
    ).json()["rows"]


def test_save_failure_never_announces_online_success_or_saves_source_selection(
    tmp_path, built
):
    reports = FakeReports()
    reports.failed = True
    app = preview.create_app(tmp_path, report_store=reports)
    response = generate(app)
    assert response.status_code == 503
    assert response.json() == {"error": "ONLINE_STORAGE_UNAVAILABLE"}
    assert reports.items == {}
    assert send(app, "GET", "/api/config").json()["saved_sources"] == {}
    assert send(app, "GET", "/api/reports").status_code == 503


def test_online_history_bounds_and_origin_guards(tmp_path):
    app = preview.create_app(tmp_path, report_store=FakeReports())
    for query in ("limit=0", "limit=101", "offset=-1", "offset=100001"):
        assert send(app, "GET", "/api/reports?" + query).status_code == 422
    assert (
        send(
            app, "GET", "/api/reports", headers={"Origin": "https://evil.test"}
        ).status_code
        == 403
    )
    assert send(app, "GET", "/api/reports/missing").status_code == 404
    assert send(app, "GET", "/api/drafts/missing/download").status_code == 404


def test_offline_configuration_does_not_claim_online(tmp_path, monkeypatch):
    monkeypatch.delenv("PSI_REPORT_DATABASE_URL", raising=False)
    app = preview.create_app(tmp_path)
    assert send(app, "GET", "/api/config").json()["report_storage"]["enabled"] is False
    assert send(app, "GET", "/api/reports").json()["reports"] == []
