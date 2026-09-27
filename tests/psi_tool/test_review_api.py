"""HTTP review contracts, asynchronous rebuilds and transaction failure boundaries."""

import asyncio
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from web import review_api
from web.online_report_store import ReportStoreError
from web.review_sources import SourceBundleError
from web.review_store import ReviewStore, ReviewStoreError, _ids, _revision

ORIGINAL = "a" * 32
NEW = "b" * 32
PROPOSAL = "c" * 32
APPLY = {
    "proposal_ids": [PROPOSAL],
    "expected_revision": 1,
    "author": "Accounting",
    "request_id": "apply-once",
}
PROPOSE = {
    "order_id": "current",
    "sku": "sku",
    "action": "exclude_preorder",
    "note": "Incorrect preorder",
    "author": "Accounting",
    "expected_revision": 1,
    "request_id": "proposal-once",
}


@pytest.fixture
def setup(monkeypatch):
    state = SimpleNamespace(
        baseline=None,
        bundled=False,
        analyzed=[],
        proposed=[],
        applied=[],
        approved=[],
        approved_cutoffs=[],
        committed=0,
        rolled_back=0,
        saved=[],
        connection=object(),
        failure=None,
        records={ORIGINAL: {"id": ORIGINAL, "as_of": "2026-09-03"}},
    )

    class Reports:
        def payload(self, report_id):
            assert report_id == ORIGINAL
            return {"prior_psi_sha256": "prior-hash", "crm_final_rows": [["current"]]}

        def get(self, report_id):
            return deepcopy(state.records[report_id])

        def save(self, draft, *, connection):
            assert connection is state.connection
            assert draft == "validated-draft"
            state.saved.append(connection)
            if state.failure == "report":
                raise ReportStoreError("REPORT_SAVE_FAILED")
            state.records[NEW] = {"id": NEW, "as_of": "2026-09-03"}
            return self.get(NEW)

    class Reviews:
        def approved_exclusions(self, cutoff):
            state.approved_cutoffs.append(cutoff)
            return state.approved

        def list(self, report_id):
            return {"revision": 1, "proposals": [], "events": []}

        def propose(self, report_id, **data):
            state.proposed.append(data)
            return {"id": PROPOSAL, **data}

        def applied_result(self, report_id, request_id, ids, author, revision):
            _ids(ids)
            _revision(revision)
            return NEW if state.applied else None

        def snapshot(self, report_id, ids, revision):
            _ids(ids)
            _revision(revision)
            if revision != 1:
                raise ReviewStoreError("REVIEW_REVISION_CONFLICT")
            return {"proposals": [{"id": PROPOSAL, **PROPOSE}]}

        @contextmanager
        def locked(self, report_id):
            before = deepcopy(state.records)
            try:
                yield self, state.connection
            except Exception:
                state.records = before
                state.rolled_back += 1
                raise
            else:
                state.committed += 1

        def record_applied(self, report_id, ids, new_id, author, request_id, revision):
            assert new_id in state.records
            assert report_id != new_id
            state.applied.append((report_id, new_id))

    class Bundles:
        def available(self, report_id):
            return state.bundled

        def load(self, report_id):
            return "snapshots", SimpleNamespace(content=b"baseline")

        def save(self, report_id, snapshots, baseline):
            assert report_id == NEW and snapshots == "updated"
            if state.failure == "bundle":
                raise SourceBundleError("REVIEW_SOURCE_SAVE_FAILED")

    class Sources:
        def list(self):
            return {"prior_psi": state.baseline}

        def resolve(self, kind, source_id):
            return SimpleNamespace(content=b"late-baseline")

    def analyze(payload, prior_workbook):
        state.analyzed.append(prior_workbook)
        return {
            "mismatches": [],
            "changes": [{"id": "removed", "order_id": "historical", "sku": "old"}],
            "preorder_checks": [
                {"id": "current-row", "order_id": "current", "sku": "sku"}
            ],
            "baseline_available": prior_workbook is not None,
        }

    monkeypatch.setattr(review_api, "analyze_report", analyze)
    monkeypatch.setattr(review_api, "ai_status", lambda: {"available": False})
    monkeypatch.setattr(
        review_api, "merge_applied_exclusions", lambda snapshots, *args: snapshots
    )
    monkeypatch.setattr(review_api, "apply_exclusions", lambda *args: "updated")
    monkeypatch.setattr(review_api, "build_draft", lambda *args: "validated-draft")
    app = FastAPI()
    review_api.attach_review_routes(
        app, Reports(), Reviews(), Bundles(), Sources(), asyncio.Lock()
    )
    state.app = app
    return state


def client_for(state):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=state.app), base_url="http://test"
    )


async def finished(client, job_id):
    for _ in range(200):
        response = await client.get(f"/api/review-jobs/{job_id}")
        assert response.status_code == 200
        value = response.json()
        assert "request_hash" not in value
        if value["status"] != "running":
            return value
        await asyncio.sleep(0.01)
    pytest.fail("Review job did not finish")


def test_review_load_rechecks_late_baseline_without_stale_cache(setup):
    async def run():
        async with client_for(setup) as client:
            first = await client.get(f"/api/reports/{ORIGINAL}/review")
            assert first.status_code == 200
            assert first.json()["proposals"] == {
                "revision": 1,
                "items": [],
                "events": [],
            }
            assert first.json()["can_rebuild"] is False
            assert first.json()["baseline_available"] is False
            setup.baseline = {"sha256": "prior-hash", "id": "saved-prior"}
            second = await client.get(f"/api/reports/{ORIGINAL}/review")
            assert second.json()["baseline_available"] is True
            assert setup.analyzed == [None, b"late-baseline"]

    asyncio.run(run())


@pytest.mark.parametrize(
    "data",
    [
        {**PROPOSE, "order_id": "historical", "sku": "old", "action": "exclude_order"},
        {**PROPOSE, "order_id": "unknown"},
    ],
)
def test_cannot_exclude_removed_or_unknown_order(setup, data):
    async def run():
        async with client_for(setup) as client:
            response = await client.post(
                f"/api/reports/{ORIGINAL}/proposals", json=data
            )
            assert response.status_code == 422
            assert response.json()["detail"] == "REVIEW_ORDER_NOT_FOUND"
            assert setup.proposed == []

    asyncio.run(run())


@pytest.mark.parametrize(
    "data",
    [
        {**PROPOSE, "expected_revision": True},
        {**PROPOSE, "note": []},
        {**PROPOSE, "extra": "unexpected"},
        {},
        [],
    ],
)
def test_malformed_proposals_rejected_before_store(setup, data):
    async def run():
        async with client_for(setup) as client:
            response = await client.post(
                f"/api/reports/{ORIGINAL}/proposals", json=data
            )
            assert response.status_code == 422
            assert setup.proposed == []

    asyncio.run(run())


def test_async_apply_commits_new_report_and_idempotent_job(setup):
    async def run():
        async with client_for(setup) as client:
            first = await client.post(f"/api/reports/{ORIGINAL}/apply", json=APPLY)
            assert first.status_code == 202
            job_id = first.json()["job_id"]
            done = await finished(client, job_id)
            assert done["status"] == "completed" and done["report"]["id"] == NEW
            assert setup.records[ORIGINAL]["id"] == ORIGINAL
            assert setup.applied == [(ORIGINAL, NEW)]
            assert setup.committed == 1 and setup.rolled_back == 0
            retry = await client.post(f"/api/reports/{ORIGINAL}/apply", json=APPLY)
            assert retry.status_code == 202 and retry.json()["job_id"] == job_id
            conflict = await client.post(
                f"/api/reports/{ORIGINAL}/apply", json={**APPLY, "author": "Other"}
            )
            assert conflict.status_code == 409
            assert conflict.json()["detail"] == "REVIEW_REQUEST_CONFLICT"
            assert len(setup.saved) == 1

    asyncio.run(run())


def test_apply_merges_permanent_exclusions_before_pending_changes(setup, monkeypatch):
    setup.approved = [
        {"order_id": "excluded-last-week", "sku": "", "action": "exclude_order"}
    ]
    calls = []

    def merge(snapshots, approved, cutoff):
        assert snapshots == "snapshots"
        assert approved == setup.approved
        assert cutoff.isoformat() == "2026-09-03"
        calls.append("merge-approved")
        return "snapshots-with-permanent-exclusions"

    def apply(snapshots, proposals, cutoff, author):
        assert snapshots == "snapshots-with-permanent-exclusions"
        assert proposals == [{"id": PROPOSAL, **PROPOSE}]
        assert cutoff.isoformat() == "2026-09-03"
        assert author == APPLY["author"]
        calls.append("apply-pending")
        return "updated"

    def build(snapshots, cutoff, baseline):
        assert snapshots == "updated"
        calls.append("build")
        return "validated-draft"

    monkeypatch.setattr(review_api, "merge_applied_exclusions", merge)
    monkeypatch.setattr(review_api, "apply_exclusions", apply)
    monkeypatch.setattr(review_api, "build_draft", build)

    async def run():
        async with client_for(setup) as client:
            response = await client.post(f"/api/reports/{ORIGINAL}/apply", json=APPLY)
            assert response.status_code == 202
            done = await finished(client, response.json()["job_id"])
            assert done["status"] == "completed"
            assert calls == ["merge-approved", "apply-pending", "build"]
            assert len(setup.approved_cutoffs) == 1
            assert setup.approved_cutoffs[0].isoformat() == "2026-09-03"
            assert setup.committed == 1

    asyncio.run(run())


@pytest.mark.parametrize(
    "failure,error",
    [
        ("report", "REPORT_SAVE_FAILED"),
        ("bundle", "REVIEW_SOURCE_SAVE_FAILED"),
    ],
)
def test_async_failure_rolls_back_report_and_no_applied_event(setup, failure, error):
    setup.failure = failure

    async def run():
        async with client_for(setup) as client:
            response = await client.post(f"/api/reports/{ORIGINAL}/apply", json=APPLY)
            assert response.status_code == 202
            done = await finished(client, response.json()["job_id"])
            assert done == {"status": "failed", "error": error}
            assert set(setup.records) == {ORIGINAL}
            assert setup.rolled_back == 1 and setup.committed == 0
            assert setup.applied == []
            # A failed job releases the build gate for subsequent work.
            proposal = await client.post(
                f"/api/reports/{ORIGINAL}/proposals", json=PROPOSE
            )
            assert proposal.status_code == 200

    asyncio.run(run())


@pytest.mark.parametrize(
    "data",
    [
        {**APPLY, "proposal_ids": []},
        {**APPLY, "proposal_ids": [PROPOSAL, PROPOSAL]},
        {**APPLY, "expected_revision": True},
        {**APPLY, "author": ""},
        {**APPLY, "request_id": {}},
    ],
)
def test_invalid_apply_never_starts_build(setup, data):
    async def run():
        async with client_for(setup) as client:
            response = await client.post(f"/api/reports/{ORIGINAL}/apply", json=data)
            assert response.status_code in (409, 422)
            assert setup.saved == [] and setup.committed == 0

    asyncio.run(run())


@pytest.mark.parametrize("fail", [False, True])
def test_real_locked_store_reuses_outer_transaction_without_inner_commit(fail):
    class Connection:
        def __init__(self):
            self.enters = self.commits = self.rollbacks = 0
            self.statements = []

        def __enter__(self):
            self.enters += 1
            return self

        def __exit__(self, kind, value, traceback):
            if kind is None:
                self.commits += 1
            else:
                self.rollbacks += 1

        def execute(self, sql, parameters):
            self.statements.append((sql, parameters))

    connection = Connection()
    store = object.__new__(ReviewStore)
    store._connect = lambda: connection
    store._require_report = lambda conn, report_id: None
    store._events = lambda conn, report_id: []

    def operation():
        with store.locked(ORIGINAL) as (bound, shared):
            assert bound is not store and shared is connection
            # list() normally enters its own connection context. A bound store
            # must keep that context from committing the outer transaction.
            assert bound.list(ORIGINAL)["revision"] == 0
            assert connection.enters == 1
            assert connection.commits == connection.rollbacks == 0
            if fail:
                raise SourceBundleError("REVIEW_SOURCE_SAVE_FAILED")

    if fail:
        with pytest.raises(SourceBundleError):
            operation()
    else:
        operation()
    assert connection.commits == int(not fail)
    assert connection.rollbacks == int(fail)
    assert "pg_advisory_xact_lock" in connection.statements[0][0]
    assert connection.statements[0][1] == ("psi-review:" + ORIGINAL,)
