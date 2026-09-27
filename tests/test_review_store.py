import json
from contextlib import contextmanager
from copy import deepcopy
from datetime import date, datetime, timezone

import pytest
from web.online_report_store import OnlineReportStore, ReportStoreError, _sha
from web.review_store import ReviewStore, ReviewStoreError

REPORT = "a" * 32
NEW_REPORT = "b" * 32


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self):
        self.events = []
        self.reports = {REPORT, NEW_REPORT}
        self.report_dates = {REPORT: date(2026, 9, 3), NEW_REPORT: date(2026, 9, 10)}
        self.locks = 0

    def execute(self, sql, params):
        if sql.startswith("SELECT p.id, p.body"):
            assert "p.report_id=a.report_id" in sql
            assert "p.revision<a.revision" in sql
            assert "r.as_of<=%s" in sql
            assert "('exclude_preorder','exclude_order')" in sql
            matches = []
            for applied in self.events:
                if (
                    applied["kind"] != "applied"
                    or self.report_dates[applied["report_id"]] > params[0]
                ):
                    continue
                for proposed in self.events:
                    if (
                        proposed["id"] in applied["body"]["proposal_ids"]
                        and proposed["report_id"] == applied["report_id"]
                        and proposed["kind"] == "proposed"
                        and proposed["revision"] < applied["revision"]
                        and proposed["body"]["action"]
                        in {"exclude_order", "exclude_preorder"}
                    ):
                        matches.append(
                            {
                                "id": proposed["id"],
                                "body": proposed["body"],
                                "approved_by": applied["body"]["approver"],
                                "effective_from": self.report_dates[
                                    applied["report_id"]
                                ],
                            }
                        )
            return Result(matches)
        if sql.startswith("SELECT id FROM psi_preview.reports"):
            return Result([{"id": params[0]}] if params[0] in self.reports else [])
        if "pg_advisory_xact_lock" in sql:
            self.locks += 1
            return Result([])
        if "WHERE report_id=%s AND request_id=%s" in sql:
            return Result(
                [
                    r
                    for r in self.events
                    if r["report_id"] == params[0] and r["request_id"] == params[1]
                ]
            )
        if sql.startswith("SELECT id, revision, kind"):
            return Result(
                [
                    {k: r[k] for k in ("id", "revision", "kind", "body", "created_at")}
                    for r in self.events
                    if r["report_id"] == params[0]
                ]
            )
        if sql.startswith("INSERT INTO psi_preview.review_events"):
            keys = [
                "id",
                "report_id",
                "revision",
                "kind",
                "body",
                "request_id",
                "request_sha256",
            ]
            row = dict(zip(keys, params))
            row["body"] = row["body"].obj
            row["created_at"] = datetime.now(timezone.utc)
            self.events.append(row)
            return Result([])
        raise AssertionError(sql)


@pytest.fixture
def store():
    connection = Connection()
    result = ReviewStore("postgresql://role:secret@host.neon.tech/db")

    @contextmanager
    def connect():
        yield connection

    result._connect = connect
    result.connection = connection
    return result


def propose(store, revision=0, request_id="request-1", **changes):
    args = dict(
        report_id=REPORT,
        order_id="ORD-1",
        sku="SKU-1",
        action="exclude_preorder",
        note="Sai so luong",
        author="Ke toan",
        expected_revision=revision,
        request_id=request_id,
    )
    return store.propose(**(args | changes))


def test_proposal_is_pending_and_retry_is_idempotent(store):
    first = propose(store)
    assert propose(store) == first
    state = store.list(REPORT)
    assert state["revision"] == 1
    assert state["proposals"][0]["state"] == "proposed"
    assert len(store.connection.events) == 1
    assert store.connection.locks == 2


def test_stale_edit_and_reused_request_content_rejected(store):
    propose(store)
    with pytest.raises(ReviewStoreError, match="REVIEW_REVISION_CONFLICT"):
        propose(store, request_id="other")
    with pytest.raises(ReviewStoreError, match="REVIEW_REQUEST_CONFLICT"):
        propose(store, note="Different")
    assert len(store.connection.events) == 1


def test_superseded_exclusion_cannot_be_applied(store):
    first = propose(store)
    second = propose(store, revision=1, request_id="other", action="note")
    assert store.list(REPORT)["proposals"][0]["id"] == second["id"]
    with pytest.raises(ReviewStoreError, match="REVIEW_PROPOSAL_NOT_APPLICABLE"):
        store.snapshot(REPORT, [first["id"]], 2)
    with pytest.raises(ReviewStoreError, match="REVIEW_PROPOSAL_NOT_APPLICABLE"):
        store.snapshot(REPORT, [second["id"]], 2)
    assert len(store.list(REPORT)["events"]) == 2


def test_apply_retains_original_and_retry_idempotency(store):
    first = propose(store)
    snapshot = store.snapshot(REPORT, [first["id"]], 1)
    assert snapshot["proposals"][0]["note"] == "Sai so luong"
    args = (REPORT, [first["id"]], NEW_REPORT, "Approver", "apply-1", 1)
    applied = store.record_applied(*args)
    assert (
        store.applied_result(REPORT, "apply-1", [first["id"]], "Approver", 1)
        == NEW_REPORT
    )
    assert store.applied_result(REPORT, "unknown", [first["id"]], "Approver", 1) is None
    with pytest.raises(ReviewStoreError, match="REVIEW_REQUEST_CONFLICT"):
        store.applied_result(REPORT, "apply-1", [first["id"]], "Changed", 1)
    with pytest.raises(ReviewStoreError, match="REVIEW_REQUEST_CONFLICT"):
        store.applied_result(REPORT, "apply-1", [first["id"]], "Approver", 2)
    assert store.record_applied(*args) == applied
    assert store.list(REPORT)["proposals"][0]["new_report_id"] == NEW_REPORT
    assert store.connection.reports == {REPORT, NEW_REPORT}
    assert len(store.connection.events) == 2
    with pytest.raises(ReviewStoreError, match="REVIEW_PROPOSAL_NOT_APPLICABLE"):
        store.snapshot(REPORT, [first["id"]], 2)


def test_snapshot_revision_cas_catches_edit_during_build(store):
    first = propose(store)
    store.snapshot(REPORT, [first["id"]], 1)
    propose(store, revision=1, request_id="during-build", sku="SKU-2")
    with pytest.raises(ReviewStoreError, match="REVIEW_REVISION_CONFLICT"):
        store.record_applied(REPORT, [first["id"]], NEW_REPORT, "A", "apply", 1)
    assert all(e["kind"] == "proposed" for e in store.connection.events)


def test_target_uses_order_and_canonical_sku_pair(store):
    first = propose(store)
    second = propose(store, revision=1, request_id="sku-2", sku="SKU-2")
    third = propose(store, revision=2, request_id="order-2", order_id="ORD-2")
    state = store.list(REPORT)
    assert len(state["proposals"]) == 3
    selected = store.snapshot(REPORT, [first["id"], second["id"], third["id"]], 3)
    assert len(selected["proposals"]) == 3


def test_order_level_exclusion_and_note_accept_empty_sku(store):
    propose(store, sku="", action="exclude_order")
    propose(store, sku="", action="note", revision=1, request_id="note")
    assert len(store.list(REPORT)["proposals"]) == 1
    with pytest.raises(ReviewStoreError, match="REVIEW_INPUT_INVALID"):
        propose(store, sku="", revision=2, request_id="invalid")


def test_locked_store_uses_one_transaction_and_rolls_back_late_failure(store):
    opened = 0
    connection = store.connection

    @contextmanager
    def transaction():
        nonlocal opened
        opened += 1
        previous = deepcopy(connection.events)
        try:
            yield connection
        except Exception:
            connection.events = previous
            raise

    store._connect = transaction
    with pytest.raises(RuntimeError, match="bundle failed"):
        with store.locked(REPORT) as (bound, existing):
            assert existing is connection
            first = propose(bound)
            assert bound.snapshot(REPORT, [first["id"]], 1)["revision"] == 1
            bound.record_applied(REPORT, [first["id"]], NEW_REPORT, "A", "apply", 1)
            assert (
                bound.applied_result(REPORT, "apply", [first["id"]], "A", 1)
                == NEW_REPORT
            )
            assert len(connection.events) == 2
            raise RuntimeError("bundle failed")
    assert opened == 1
    assert connection.events == []
    assert connection.locks == 3
    assert store._connect is transaction


def test_unknown_report_cannot_read_or_propose(store):
    with pytest.raises(ReportStoreError, match="ONLINE_REPORT_NOT_FOUND"):
        store.list("c" * 32)
    with pytest.raises(ReportStoreError, match="ONLINE_REPORT_NOT_FOUND"):
        propose(store, report_id="c" * 32)
    assert not store.connection.events


def test_approved_exclusions_carry_only_applied_effective_decisions(store):
    approved = propose(store, author="Original accountant")
    assert store.approved_exclusions(date(2026, 9, 3)) == []
    store.record_applied(
        REPORT, [approved["id"]], NEW_REPORT, "Approving operator", "apply", 1
    )
    propose(store, revision=2, request_id="pending", sku="SKU-2")
    propose(store, revision=3, request_id="note", sku="SKU-3", action="note")
    assert store.approved_exclusions(date(2026, 9, 2)) == []
    decisions = store.approved_exclusions(date(2026, 9, 10))
    assert len(decisions) == 1
    assert decisions[0]["id"] == approved["id"]
    assert decisions[0]["author"] == "Original accountant"
    assert decisions[0]["approved_by"] == "Approving operator"
    assert decisions[0]["effective_from"] == "2026-09-03"
    future = propose(store, report_id=NEW_REPORT, request_id="future")
    store.record_applied(
        NEW_REPORT, [future["id"]], REPORT, "Other operator", "future-apply", 1
    )
    assert store.approved_exclusions(date(2026, 9, 3)) == decisions
    assert len(store.approved_exclusions(date(2026, 9, 10))) == 2
    store.connection.events.append(deepcopy(store.connection.events[-1]))
    assert len(store.approved_exclusions(date(2026, 9, 10))) == 2


def test_approved_exclusions_reject_non_date_cutoff(store):
    with pytest.raises(ReviewStoreError, match="REVIEW_INPUT_INVALID"):
        store.approved_exclusions("2026-09-03")


@pytest.mark.parametrize(
    "new_id,error",
    [(REPORT, "REVIEW_NEW_REPORT_REQUIRED"), ("c" * 32, "ONLINE_REPORT_NOT_FOUND")],
)
def test_apply_requires_different_existing_report(store, new_id, error):
    first = propose(store)
    with pytest.raises(ReportStoreError, match=error):
        store.record_applied(REPORT, [first["id"]], new_id, "A", "apply", 1)


@pytest.mark.parametrize(
    "changes",
    [
        {"note": ""},
        {"action": "delete"},
        {"expected_revision": True},
        {"sku": "x\x00"},
        {"author": "x" * 201},
    ],
)
def test_invalid_proposals_never_write(store, changes):
    with pytest.raises(ReportStoreError):
        propose(store, **changes)
    assert store.connection.events == []


def test_payload_verifies_both_representations():
    payload = {"as_of": "2026-09-03", "summary": {"count": 1}}
    row = {
        "payload": payload,
        "payload_json": json.dumps(payload),
        "payload_sha256": _sha(payload),
    }

    class PayloadConnection:
        def execute(self, sql, params):
            return Result([row])

    store = OnlineReportStore("postgresql://role:secret@host.neon.tech/db")

    @contextmanager
    def connect():
        yield PayloadConnection()

    store._connect = connect
    assert store.payload(REPORT) == payload
    row["payload_json"] = '{"summary": {"count": 99}}'
    with pytest.raises(ReportStoreError, match="ONLINE_REPORT_INTEGRITY_FAILED"):
        store.payload(REPORT)
