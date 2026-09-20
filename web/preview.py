"""Loopback-only PSI acceptance preview. Cloud publication is a separate adapter."""

from __future__ import annotations

import asyncio
import io
import os
import secrets
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree.ElementTree import ParseError

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from openpyxl.utils.exceptions import InvalidFileException
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from psi_tool.online_baseline import verify_baseline
from psi_tool.online_pipeline import (
    MAX_SOURCE_BYTES,
    SOURCE_LABELS,
    PipelineError,
    SourceSnapshot,
    build_draft,
)
from web.online_report_store import OnlineReportStore, ReportStoreError
from web.preview_store import (
    REUSABLE_ROLES,
    SourceStore,
    StoreError,
    default_storage_dir,
)

STATIC = Path(__file__).parent / "preview_static"
MAX_REQUEST_BYTES = MAX_SOURCE_BYTES * 8 + 1024 * 1024
INPUT_ERRORS = (
    ValueError,
    KeyError,
    OSError,
    EOFError,
    SyntaxError,
    zipfile.BadZipFile,
    ParseError,
    InvalidFileException,
)


class BodyLimitMiddleware:
    """Limit streamed multipart bodies without buffering the whole request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        total = 0

        async def limited_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > MAX_REQUEST_BYTES:
                    raise HTTPException(413, "REQUEST_TOO_LARGE")
            return message

        await self.app(scope, limited_receive, send)


def check_package(content: bytes) -> None:
    """Bound decompression before any spreadsheet parser sees untrusted bytes."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if (
                len(members) > 5000
                or sum(x.file_size for x in members) > 512 * 1024 * 1024
                or any(x.file_size > 256 * 1024 * 1024 for x in members)
                or any(x.flag_bits & 1 for x in members)
                or len({x.filename for x in members}) != len(members)
                or not {"[Content_Types].xml", "xl/workbook.xml"}
                <= {x.filename for x in members}
            ):
                raise ValueError("package limits")
    except (zipfile.BadZipFile, ValueError) as exc:
        raise HTTPException(422, "SOURCE_PACKAGE_INVALID") from exc


def create_app(
    storage_dir: Path | None = None, report_store: OnlineReportStore | None = None
) -> FastAPI:
    app = FastAPI(
        title="PSI validation preview", docs_url=None, redoc_url=None, openapi_url=None
    )
    app.add_middleware(BodyLimitMiddleware)
    token = secrets.token_urlsafe(32)
    style_nonce = secrets.token_urlsafe(24)
    app.state.style_nonce = style_nonce
    store = SourceStore(
        storage_dir if storage_dir is not None else default_storage_dir()
    )
    from web.review_sources import SourceBundleStore, merge_applied_exclusions
    from web.review_store import ReviewStore
    from web.review_api import attach_review_routes

    bundles = SourceBundleStore(Path(os.environ.get("PSI_REPORT_SOURCE_DIR", str((storage_dir or default_storage_dir()).parent / "report-sources"))))
    gate = asyncio.Semaphore(1)
    drafts: dict[str, bytes] = {}
    database_url = os.environ.get("PSI_REPORT_DATABASE_URL")
    reports = report_store
    if reports is None and database_url:
        reports = OnlineReportStore(database_url)
    reviews = ReviewStore(database_url) if database_url else None
    attach_review_routes(app, reports, reviews, bundles, store, gate)

    @app.middleware("http")
    async def loopback_only(request: Request, call_next):
        host = request.url.hostname
        client = request.client.host if request.client else ""
        if host not in {
            "localhost",
            "127.0.0.1",
            "::1",
            "testserver",
        } or client not in {
            "127.0.0.1",
            "::1",
            "testclient",
        }:
            return JSONResponse({"error": "LOCAL_PREVIEW_ONLY"}, 403)
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host"):
            return JSONResponse({"error": "ORIGIN_FORBIDDEN"}, 403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"error": "ORIGIN_FORBIDDEN"}, 403)
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and request.headers.get("x-psi-preview") != token
        ):
            return JSONResponse({"error": "PREVIEW_TOKEN_REQUIRED"}, 403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; "
            f"style-src 'self' 'nonce-{style_nonce}'; style-src-attr 'unsafe-inline'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @app.exception_handler(StoreError)
    async def store_error(request: Request, exc: StoreError):
        return JSONResponse({"error": str(exc)}, 409)

    @app.exception_handler(ReportStoreError)
    async def report_store_error(request: Request, exc: ReportStoreError):
        code = str(exc)
        status = 404 if code == "ONLINE_REPORT_NOT_FOUND" else 503
        if code in {"REPORT_PAGE_INVALID", "REPORT_SHEET_INVALID"}:
            status = 422
        return JSONResponse({"error": code}, status)

    async def read_upload(upload: UploadFile) -> SourceSnapshot:
        filename = (
            (upload.filename or "upload.xlsx").replace("\\", "/").rsplit("/", 1)[-1]
        )
        if not filename.lower().endswith(".xlsx") or len(filename) > 255:
            raise HTTPException(422, "SOURCE_EXTENSION_INVALID")
        content = await upload.read(MAX_SOURCE_BYTES + 1)
        if not 0 < len(content) <= MAX_SOURCE_BYTES:
            raise HTTPException(413, "SOURCE_SIZE_INVALID")
        check_package(content)
        return SourceSnapshot.from_bytes(filename, content)

    @app.get("/health")
    async def health():
        return {"ok": True, "mode": "local-acceptance-preview", "publication": False}

    @app.get("/api/config")
    async def config():
        return {
            "preview_token": token,
            "sources": SOURCE_LABELS,
            "style_nonce": style_nonce,
            "saved_sources": await run_in_threadpool(store.list),
            "report_storage": {
                "enabled": reports is not None,
                "provider": "neon" if reports is not None else None,
            },
        }

    @app.get("/api/reports")
    async def history(
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0, le=100000),
    ):
        items = await run_in_threadpool(reports.list, limit, offset) if reports else []
        return {"reports": items, "limit": limit, "offset": offset}

    @app.get("/api/reports/{report_id}")
    async def report_detail(report_id: str):
        item = await run_in_threadpool(reports.get, report_id) if reports else None
        if item is None:
            raise HTTPException(404, "ONLINE_REPORT_NOT_FOUND")
        return item

    @app.get("/api/reports/{report_id}/sheets")
    async def report_sheets(report_id: str):
        if reports is None:
            raise HTTPException(404, "ONLINE_REPORT_NOT_FOUND")
        return {"sheets": await run_in_threadpool(reports.sheets, report_id)}

    @app.get("/api/reports/{report_id}/sheets/{ordinal}/rows")
    async def report_sheet_rows(
        report_id: str,
        ordinal: int,
        limit: int = Query(100, ge=1, le=100),
        offset: int = Query(0, ge=0, le=100000),
    ):
        if reports is None:
            raise HTTPException(404, "ONLINE_REPORT_NOT_FOUND")
        return {
            "rows": await run_in_threadpool(
                reports.sheet_rows, report_id, ordinal, limit, offset
            ),
            "limit": limit,
            "offset": offset,
        }

    @app.post("/api/sources/classify")
    async def classify(request: Request):
        from web.preview_classify import classify_files

        async with request.form(
            max_files=4, max_fields=0, max_part_size=MAX_SOURCE_BYTES
        ) as form:
            uploads = form.getlist("files")
            if (
                set(form) != {"files"}
                or not 1 <= len(uploads) <= 4
                or any(not isinstance(upload, UploadFile) for upload in uploads)
            ):
                raise HTTPException(422, "CLASSIFICATION_FILES_INVALID")
            snapshots = [await read_upload(upload) for upload in uploads]
            try:
                results = await run_in_threadpool(
                    classify_files,
                    [(snapshot.filename, snapshot.content) for snapshot in snapshots],
                )
            except INPUT_ERRORS:
                raise HTTPException(422, "SOURCE_SCHEMA_INVALID") from None
        return {"files": results}

    @app.post("/api/sources/{role}")
    async def save_source(role: str, request: Request):
        from web.preview_classify import validate_reusable

        if role not in REUSABLE_ROLES:
            raise HTTPException(422, "SAVED_SOURCE_ROLE_INVALID")
        if gate.locked():
            raise HTTPException(409, "BUILD_IN_PROGRESS")
        async with gate:
            async with request.form(
                max_files=1, max_fields=0, max_part_size=MAX_SOURCE_BYTES
            ) as form:
                if (
                    set(form) != {"file"}
                    or len(form.getlist("file")) != 1
                    or not isinstance(form["file"], UploadFile)
                ):
                    raise HTTPException(422, "SOURCE_FILE_REQUIRED")
                snapshot = await read_upload(form["file"])
                try:
                    if role == "prior_psi":
                        await run_in_threadpool(
                            verify_baseline,
                            snapshot.content,
                            snapshot.filename,
                            date.max,
                        )
                    else:
                        await run_in_threadpool(
                            validate_reusable, role, snapshot.filename, snapshot.content
                        )
                except INPUT_ERRORS:
                    raise HTTPException(422, "SOURCE_SCHEMA_INVALID") from None
                saved = await run_in_threadpool(store.save_many, {role: snapshot})
        return saved[role]

    @app.delete("/api/sources/{role}")
    async def clear_source(role: str):
        if role not in REUSABLE_ROLES:
            raise HTTPException(422, "SAVED_SOURCE_ROLE_INVALID")
        if gate.locked():
            raise HTTPException(409, "BUILD_IN_PROGRESS")
        async with gate:
            return {"saved_sources": await run_in_threadpool(store.clear, role)}

    @app.post("/api/drafts")
    async def generate(request: Request):
        if gate.locked():
            raise HTTPException(409, "BUILD_IN_PROGRESS")
        async with gate:
            async with request.form(
                max_files=8, max_fields=5, max_part_size=MAX_SOURCE_BYTES
            ) as form:
                if set(form) != set(SOURCE_LABELS) | {"prior_psi", "as_of"} or any(
                    len(form.getlist(k)) != 1 for k in form
                ):
                    raise HTTPException(422, "SOURCE_SET_INVALID")
                try:
                    cutoff = date.fromisoformat(str(form["as_of"]))
                except ValueError as exc:
                    raise HTTPException(422, "CUTOFF_INVALID") from exc
                snapshots = {}
                uploaded_reusable = {}
                for key in [*SOURCE_LABELS, "prior_psi"]:
                    upload = form[key]
                    if isinstance(upload, UploadFile):
                        snapshots[key] = await read_upload(upload)
                        if key in REUSABLE_ROLES:
                            uploaded_reusable[key] = snapshots[key]
                    elif key in REUSABLE_ROLES and isinstance(upload, str):
                        snapshots[key] = await run_in_threadpool(
                            store.resolve, key, upload
                        )
                    else:
                        raise HTTPException(422, "SOURCE_FILE_REQUIRED")
                baseline = snapshots.pop("prior_psi")
                if reviews is not None:
                    decisions = await run_in_threadpool(reviews.approved_exclusions, cutoff)
                    snapshots = await run_in_threadpool(merge_applied_exclusions, snapshots, decisions, cutoff)
                try:
                    result = await run_in_threadpool(
                        build_draft, snapshots, cutoff, baseline
                    )
                except PipelineError as exc:
                    return JSONResponse({"error": exc.code, "status": "FAIL"}, 422)
                except INPUT_ERRORS:
                    return JSONResponse(
                        {"error": "SOURCE_VALIDATION_FAILED", "status": "FAIL"}, 422
                    )
            # Commit the entire validated snapshot before announcing online success.
            online_report = (
                await run_in_threadpool(reports.save, result) if reports else None
            )
            if online_report is not None:
                await run_in_threadpool(bundles.save, online_report["id"], snapshots, baseline)
            saved_sources = (
                await run_in_threadpool(store.save_missing, uploaded_reusable)
                if uploaded_reusable
                else await run_in_threadpool(store.list)
            )
            if online_report is not None:
                return {**online_report, "saved_sources": saved_sources}
            draft_id = secrets.token_hex(16)
            drafts.clear()  # Only the most recent preview is kept in memory.
            drafts[draft_id] = result.xlsx
            return {
                "id": draft_id,
                "saved_sources": saved_sources,
                "state": "draft",
                "storage": "local",
                "input_hash": result.input_hash,
                "workbook_sha256": result.workbook_sha256,
                "summary": result.payload.get("summary", {}),
                "gates": result.payload.get("gates", []),
                "validation": {
                    "payload": "PASS",
                    "parquet": "PASS",
                    "workbook": "PASS",
                },
                "download_url": f"/api/drafts/{draft_id}/download",
            }

    @app.get("/api/drafts/{draft_id}/download")
    async def download(draft_id: str):
        if reports is not None:
            async with gate:
                content = await run_in_threadpool(reports.download, draft_id)
        elif draft_id in drafts:
            content = drafts[draft_id]
        else:
            raise HTTPException(404, "DRAFT_NOT_FOUND")
        return Response(
            content,
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={"Content-Disposition": 'attachment; filename="PSI_Draft.xlsx"'},
        )

    @app.get("/")
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/app.js")
    async def script():
        return FileResponse(STATIC / "app.js", media_type="text/javascript")

    @app.get("/styles.css")
    async def style():
        return FileResponse(STATIC / "styles.css", media_type="text/css")

    return app


app = create_app()
