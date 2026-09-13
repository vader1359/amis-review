"""Append-only accounting suggestions; applying never mutates a saved report."""

from __future__ import annotations

import hashlib
import re
import uuid
from contextlib import contextmanager, nullcontext
from copy import copy
from datetime import date
from typing import Any

from psycopg.types.json import Jsonb

from web.online_report_store import (
    OnlineReportStore,
    ReportStoreError,
    _json,
    _report_id,
)


class ReviewStoreError(ReportStoreError):
    pass


def _text(value: Any, maximum: int, *, empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ReviewStoreError("REVIEW_INPUT_INVALID")
    value = value.strip()
    if (
        (not value and not empty)
        or len(value) > maximum
        or any(ord(char) < 32 and char not in "\n\t" for char in value)
    ):
        raise ReviewStoreError("REVIEW_INPUT_INVALID")
    return value


def _revision(value: int) -> int:
    if type(value) is not int or value < 0:
        raise ReviewStoreError("REVIEW_INPUT_INVALID")
    return value


def _ids(values: list[str]) -> list[str]:
    if not isinstance(values, list) or not 1 <= len(values) <= 500:
        raise ReviewStoreError("REVIEW_INPUT_INVALID")
    if any(
        not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value)
        for value in values
    ):
        raise ReviewStoreError("REVIEW_INPUT_INVALID")
    if len(set(values)) != len(values):
        raise ReviewStoreError("REVIEW_INPUT_INVALID")
    return sorted(values)


def _state(events: list[dict]) -> dict:
    latest = {}
    applied = {}
    for event in events:
        body = event["body"]
        if event["kind"] == "proposed":
            latest[(body["order_id"], body["sku"])] = {
                **body,
                "id": event["id"],
                "revision": event["revision"],
                "created_at": event["created_at"],
                "state": "proposed",
            }
        else:
            for proposal_id in body["proposal_ids"]:
                applied[proposal_id] = body["new_report_id"]
    for proposal in latest.values():
        if proposal["id"] in applied:
            proposal.update(state="applied", new_report_id=applied[proposal["id"]])
    return {
        "revision": events[-1]["revision"] if events else 0,
        "proposals": list(latest.values()),
        "events": events,
    }


class ReviewStore(OnlineReportStore):
    """A per-report advisory lock plus unique revision protects concurrent writes.

    Callers must verify that the supplied canonical order/SKU exists in the report.
    Actor labels are recorded for attribution, not treated as authentication.
    """

    def approved_exclusions(self, as_of: date) -> list[dict]:
        """Carry explicitly applied exclusions into later report periods.

        Pending suggestions and notes have no effect. Preserve the proposal's
        author separately from the operator who approved its application.
        """
        if type(as_of) is not date:
            raise ReviewStoreError("REVIEW_INPUT_INVALID")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT p.id, p.body, a.body->>'approver' AS approved_by, "
                "r.as_of AS effective_from "
                "FROM psi_preview.review_events a "
                "JOIN psi_preview.reports r ON r.id=a.report_id "
                "CROSS JOIN LATERAL jsonb_array_elements_text("
                "CASE WHEN a.kind='applied' THEN a.body->'proposal_ids' "
                "ELSE '[]'::jsonb END) AS selected(proposal_id) "
                "JOIN psi_preview.review_events p "
                "ON p.id=selected.proposal_id AND p.report_id=a.report_id "
                "AND p.kind='proposed' AND p.revision<a.revision "
                "WHERE a.kind='applied' AND r.as_of<=%s "
                "AND p.body->>'action' IN ('exclude_preorder','exclude_order') "
                "ORDER BY r.as_of, a.created_at, a.id, p.id",
                (as_of,),
            ).fetchall()
        seen = set()
        decisions = []
        for row in rows:
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            decisions.append(
                {
                    **row["body"],
                    "id": row["id"],
                    "approved_by": row["approved_by"],
                    "effective_from": row["effective_from"].isoformat(),
                }
            )
        return decisions

    @contextmanager
    def locked(self, report_id: str):
        """Hold one transaction and report lock through build, save and audit.

        Use the yielded store only within this context. Its methods reuse the
        transaction without committing, so an exception rolls back both a newly
        saved report and its accounting event together.
        """
        report_id = _report_id(report_id)
        with self._connect() as connection:
            self._require_report(connection, report_id)
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                ("psi-review:" + report_id,),
            )
            bound = copy(self)
            bound._connect = lambda: nullcontext(connection)
            yield bound, connection

    @staticmethod
    def _events(connection, report_id: str) -> list[dict]:
        rows = connection.execute(
            "SELECT id, revision, kind, body, created_at "
            "FROM psi_preview.review_events "
            "WHERE report_id=%s ORDER BY revision",
            (report_id,),
        ).fetchall()
        return [{**row, "created_at": row["created_at"].isoformat()} for row in rows]

    def list(self, report_id: str) -> dict:
        with self._connect() as connection:
            self._require_report(connection, report_id)
            return _state(self._events(connection, report_id))

    @staticmethod
    def _selection(
        state: dict, proposal_ids: list[str], expected_revision: int
    ) -> list[dict]:
        if state["revision"] != expected_revision:
            raise ReviewStoreError("REVIEW_REVISION_CONFLICT")
        selected = [p for p in state["proposals"] if p["id"] in proposal_ids]
        if len(selected) != len(proposal_ids) or any(
            p["state"] != "proposed" or p["action"] == "note" for p in selected
        ):
            raise ReviewStoreError("REVIEW_PROPOSAL_NOT_APPLICABLE")
        return selected

    def snapshot(
        self, report_id: str, proposal_ids: list[str], expected_revision: int
    ) -> dict:
        ids = _ids(proposal_ids)
        state = self.list(report_id)
        return {
            "revision": state["revision"],
            "proposals": self._selection(state, ids, _revision(expected_revision)),
        }

    def _append(
        self,
        report_id: str,
        kind: str,
        body: dict,
        expected_revision: int,
        request_id: str,
    ) -> dict:
        report_id = _report_id(report_id)
        expected_revision = _revision(expected_revision)
        request_id = _text(request_id, 128)
        digest = hashlib.sha256(
            _json({"kind": kind, "body": body, "expected_revision": expected_revision})
        ).hexdigest()
        with self._connect() as connection:
            self._require_report(connection, report_id)
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                ("psi-review:" + report_id,),
            )
            previous = connection.execute(
                "SELECT id, revision, request_sha256 FROM psi_preview.review_events "
                "WHERE report_id=%s AND request_id=%s",
                (report_id, request_id),
            ).fetchone()
            if previous:
                if previous["request_sha256"] != digest:
                    raise ReviewStoreError("REVIEW_REQUEST_CONFLICT")
                return {
                    "id": previous["id"],
                    "revision": previous["revision"],
                    "kind": kind,
                    **body,
                }
            state = _state(self._events(connection, report_id))
            if state["revision"] != expected_revision:
                raise ReviewStoreError("REVIEW_REVISION_CONFLICT")
            if kind == "applied":
                self._selection(state, body["proposal_ids"], expected_revision)
                if body["new_report_id"] == report_id:
                    raise ReviewStoreError("REVIEW_NEW_REPORT_REQUIRED")
                self._require_report(connection, body["new_report_id"])
            event_id = uuid.uuid4().hex
            revision = expected_revision + 1
            connection.execute(
                "INSERT INTO psi_preview.review_events "
                "(id, report_id, revision, kind, body, request_id, request_sha256) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (event_id, report_id, revision, kind, Jsonb(body), request_id, digest),
            )
            return {"id": event_id, "revision": revision, "kind": kind, **body}

    def propose(
        self,
        report_id: str,
        order_id: str,
        sku: str,
        action: str,
        note: str,
        author: str,
        expected_revision: int,
        request_id: str,
    ) -> dict:
        if action not in {"note", "exclude_preorder", "exclude_order"}:
            raise ReviewStoreError("REVIEW_ACTION_INVALID")
        return self._append(
            report_id,
            "proposed",
            {
                "order_id": _text(order_id, 200),
                "sku": _text(sku, 200, empty=action in {"exclude_order", "note"}),
                "action": action,
                "note": _text(note, 4000),
                "author": _text(author, 200),
            },
            expected_revision,
            request_id,
        )

    def record_applied(
        self,
        report_id: str,
        proposal_ids: list[str],
        new_report_id: str,
        approver: str,
        request_id: str,
        expected_revision: int,
    ) -> dict:
        return self._append(
            report_id,
            "applied",
            {
                "proposal_ids": _ids(proposal_ids),
                "new_report_id": _report_id(new_report_id),
                "approver": _text(approver, 200),
            },
            expected_revision,
            request_id,
        )

    def applied_result(
        self,
        report_id: str,
        request_id: str,
        proposal_ids: list[str],
        author: str,
        expected_revision: int,
    ) -> str | None:
        """Recover an identical completed apply before regenerating a workbook."""
        report_id = _report_id(report_id)
        request_id = _text(request_id, 128)
        proposal_ids = _ids(proposal_ids)
        author = _text(author, 200)
        expected_revision = _revision(expected_revision)
        with self._connect() as connection:
            self._require_report(connection, report_id)
            previous = connection.execute(
                "SELECT kind, body, request_sha256 FROM psi_preview.review_events "
                "WHERE report_id=%s AND request_id=%s",
                (report_id, request_id),
            ).fetchone()
        if previous is None:
            return None
        body = previous["body"]
        if previous["kind"] != "applied" or "new_report_id" not in body:
            raise ReviewStoreError("REVIEW_REQUEST_CONFLICT")
        expected_body = {
            "proposal_ids": proposal_ids,
            "new_report_id": body["new_report_id"],
            "approver": author,
        }
        digest = hashlib.sha256(
            _json(
                {
                    "kind": "applied",
                    "body": expected_body,
                    "expected_revision": expected_revision,
                }
            )
        ).hexdigest()
        if previous["request_sha256"] != digest:
            raise ReviewStoreError("REVIEW_REQUEST_CONFLICT")
        return body["new_report_id"]
