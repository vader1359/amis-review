"""Post-export review; corrections always rebuild a separate validated Draft."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import threading
from collections import OrderedDict
from datetime import date

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from psi_tool.online_pipeline import PipelineError, build_draft
from psi_tool.online_review import analyze_report
from web.online_report_store import ReportStoreError
from web.review_ai import ai_status, explain_review
from web.review_sources import (
    SourceBundleError,
    apply_exclusions,
    merge_applied_exclusions,
)
from web.review_store import ReviewStoreError


def attach_review_routes(app, reports, reviews, bundles, source_store, gate):
    cache = OrderedDict()
    cache_lock = threading.Lock()
    jobs = OrderedDict()
    tasks = set()
    ai_gate = asyncio.Semaphore(1)

    def require_enabled():
        if reports is None or reviews is None:
            raise HTTPException(503, "REVIEW_STORAGE_UNAVAILABLE")

    def evidence(report_id):
        require_enabled()
        with cache_lock:
            if report_id in cache:
                cache.move_to_end(report_id)
                return cache[report_id]
        payload = reports.payload(report_id)
        baseline = None
        can_rebuild = False
        if bundles.available(report_id):
            _, baseline = bundles.load(report_id)
            can_rebuild = True
        else:
            current = source_store.list().get("prior_psi")
            if current and current.get("sha256") == payload.get("prior_psi_sha256"):
                baseline = source_store.resolve("prior_psi", current["id"])
        result = analyze_report(
            payload, prior_workbook=baseline.content if baseline else None
        )
        result["can_rebuild"] = can_rebuild
        if can_rebuild:
            with cache_lock:
                cache[report_id] = result
                while len(cache) > 8:
                    cache.popitem(last=False)
        return result

    async def body(request):
        try:
            raw = bytearray()
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw) > 32768:
                    raise ValueError
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError
            return value
        except (ValueError, TypeError):
            raise HTTPException(422, "REVIEW_INPUT_INVALID") from None

    @app.exception_handler(ReviewStoreError)
    async def review_error(request, exc):
        from starlette.responses import JSONResponse

        return JSONResponse({"error": exc.code}, 409)

    @app.exception_handler(SourceBundleError)
    async def source_error(request, exc):
        from starlette.responses import JSONResponse

        return JSONResponse({"error": exc.code}, 409)

    @app.get("/api/reports/{report_id}/review")
    async def review(report_id: str):
        result = copy.deepcopy(await run_in_threadpool(evidence, report_id))
        state = await run_in_threadpool(reviews.list, report_id)
        result["proposals"] = {
            "revision": state["revision"],
            "items": state["proposals"],
            "events": state["events"],
        }
        result["ai"] = ai_status()
        return result

    @app.post("/api/reports/{report_id}/proposals")
    async def propose(report_id: str, request: Request):
        require_enabled()
        data = await body(request)
        required = {
            "order_id",
            "sku",
            "action",
            "note",
            "author",
            "expected_revision",
            "request_id",
        }
        if (
            set(data) != required
            or any(
                not isinstance(data[k], str)
                for k in ("order_id", "sku", "action", "note", "author", "request_id")
            )
            or type(data["expected_revision"]) is not int
        ):
            raise HTTPException(422, "REVIEW_INPUT_INVALID")
        if gate.locked():
            raise HTTPException(409, "BUILD_IN_PROGRESS")
        async with gate:
            result = await run_in_threadpool(evidence, report_id)
            rows = result["preorder_checks"] + result["changes"] + result["mismatches"]
            identities = {(row.get("order_id"), row.get("sku")) for row in rows}
            order, sku = data["order_id"], data["sku"]
            if not isinstance(order, str) or not isinstance(sku, str) or not order:
                raise HTTPException(422, "REVIEW_ORDER_NOT_FOUND")
            if data["action"] == "exclude_order":
                payload = await run_in_threadpool(reports.payload, report_id)
                current_orders = (
                    {str(row[0]).strip() for row in payload.get("crm_final_rows", [])}
                    | {str(row[11]).strip() for row in payload.get("revenue_rows", [])}
                    | {str(row[12]).strip() for row in payload.get("preorder_rows", [])}
                )
                if order not in current_orders:
                    raise HTTPException(422, "REVIEW_ORDER_NOT_FOUND")
                data["sku"] = ""
            elif (order, sku) not in identities:
                raise HTTPException(422, "REVIEW_ORDER_NOT_FOUND")
            if data["action"] == "exclude_preorder" and not any(
                row.get("order_id") == order and row.get("sku") == sku
                for row in result["preorder_checks"]
            ):
                raise HTTPException(422, "REVIEW_PREORDER_NOT_FOUND")
            return await run_in_threadpool(reviews.propose, report_id, **data)

    @app.post("/api/reports/{report_id}/apply")
    async def apply(report_id: str, request: Request):
        require_enabled()
        data = await body(request)
        if set(data) != {"proposal_ids", "expected_revision", "author", "request_id"}:
            raise HTTPException(422, "REVIEW_INPUT_INVALID")
        if (
            not isinstance(data["author"], str)
            or not 1 <= len(data["author"].strip()) <= 120
        ):
            raise HTTPException(422, "REVIEW_INPUT_INVALID")
        if (
            not isinstance(data["request_id"], str)
            or not 1 <= len(data["request_id"]) <= 128
        ):
            raise HTTPException(422, "REVIEW_INPUT_INVALID")
        job_id = hashlib.sha256(
            f"{report_id}:{data['request_id']}".encode()
        ).hexdigest()[:32]
        request_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
        if job_id in jobs:
            if jobs[job_id]["request_hash"] != request_hash:
                raise HTTPException(409, "REVIEW_REQUEST_CONFLICT")
            if jobs[job_id]["status"] != "failed":
                return JSONResponse(
                    {"job_id": job_id, "status": jobs[job_id]["status"]}, 202
                )
            del jobs[job_id]
        if gate.locked():
            raise HTTPException(409, "BUILD_IN_PROGRESS")
        # Validate proposal selection before accepting a long-running job.
        previous = await run_in_threadpool(
            reviews.applied_result,
            report_id,
            data["request_id"],
            data["proposal_ids"],
            data["author"],
            data["expected_revision"],
        )
        if not previous:
            await run_in_threadpool(
                reviews.snapshot,
                report_id,
                data["proposal_ids"],
                data["expected_revision"],
            )

        def rebuild():
            # One database transaction owns the lock, new report and audit link.
            # Files are published before commit; failures leave no visible DB report.
            with reviews.locked(report_id) as (locked, connection):
                previous = locked.applied_result(
                    report_id,
                    data["request_id"],
                    data["proposal_ids"],
                    data["author"],
                    data["expected_revision"],
                )
                if previous:
                    return reports.get(previous)
                selection = locked.snapshot(
                    report_id, data["proposal_ids"], data["expected_revision"]
                )
                original = reports.get(report_id)
                snapshots, baseline = bundles.load(report_id)
                cutoff = date.fromisoformat(original["as_of"])
                snapshots = merge_applied_exclusions(
                    snapshots, locked.approved_exclusions(cutoff), cutoff
                )
                updated = apply_exclusions(
                    snapshots, selection["proposals"], cutoff, data["author"]
                )
                try:
                    draft = build_draft(updated, cutoff, baseline)
                except PipelineError as exc:
                    raise HTTPException(422, exc.code) from None
                saved = reports.save(draft, connection=connection)
                bundles.save(saved["id"], updated, baseline)
                locked.record_applied(
                    report_id,
                    data["proposal_ids"],
                    saved["id"],
                    data["author"],
                    data["request_id"],
                    data["expected_revision"],
                )
                return saved

        if job_id in jobs:
            return JSONResponse(
                {"job_id": job_id, "status": jobs[job_id]["status"]}, 202
            )
        if gate.locked():
            raise HTTPException(409, "BUILD_IN_PROGRESS")
        await gate.acquire()
        jobs[job_id] = {"status": "running", "request_hash": request_hash}
        while len(jobs) > 32:
            jobs.popitem(last=False)

        async def execute():
            try:
                saved = await run_in_threadpool(rebuild)
                jobs[job_id].update(status="completed", report=saved)
            except (ReportStoreError, SourceBundleError, PipelineError) as exc:
                jobs[job_id].update(status="failed", error=exc.code)
            except HTTPException as exc:
                jobs[job_id].update(status="failed", error=str(exc.detail))
            except Exception:
                jobs[job_id].update(status="failed", error="REVIEW_BUILD_FAILED")
            finally:
                gate.release()

        task = asyncio.create_task(execute())
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return JSONResponse({"job_id": job_id, "status": "running"}, 202)

    @app.get("/api/review-jobs/{job_id}")
    async def job_status(job_id: str):
        if job_id not in jobs:
            raise HTTPException(404, "REVIEW_JOB_NOT_FOUND")
        return {
            key: value for key, value in jobs[job_id].items() if key != "request_hash"
        }

    @app.post("/api/reports/{report_id}/explain")
    async def explain(report_id: str, request: Request):
        data = await body(request)
        ids = data.get("item_ids")
        if (
            set(data) != {"item_ids"}
            or not isinstance(ids, list)
            or not 1 <= len(ids) <= 12
            or any(not isinstance(item, str) for item in ids)
        ):
            raise HTTPException(422, "REVIEW_INPUT_INVALID")
        result = await run_in_threadpool(evidence, report_id)
        selected = {
            key: [row for row in result[key] if row["id"] in ids]
            for key in ("mismatches", "changes", "preorder_checks")
        }
        if sum(len(rows) for rows in selected.values()) != len(set(ids)):
            raise HTTPException(422, "REVIEW_ITEM_NOT_FOUND")
        if ai_gate.locked():
            raise HTTPException(429, "REVIEW_AI_BUSY")
        async with ai_gate:
            return await run_in_threadpool(explain_review, selected)
