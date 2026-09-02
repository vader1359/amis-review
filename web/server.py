"""PSI shared MVP API.  Service-role credentials are server-side only."""
from __future__ import annotations

import asyncio, hashlib, io, json, os, re, uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from psi_engine.config import LOGIN_EMAILS, REQUIRED_SOURCES, SOURCE_LABELS, SOURCE_OWNERS, may_upload
from psi_engine.engine import build
from psi_engine.manual_check import load_manual_check
from psi_engine.reconcile import reconcile_with_manual_check

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")
MAX_BYTES = 50 * 1024 * 1024

class Supabase:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.anon = os.getenv("SUPABASE_ANON_KEY", "")
        self.service = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    @property
    def configured(self): return bool(self.url and self.anon and self.service)
    def headers(self, token: str | None = None, service: bool = True):
        key = self.service if service else self.anon
        return {"apikey": key, "Authorization": f"Bearer {token or key}"}
    async def request(self, method: str, path: str, *, token: str | None = None, service=True, **kwargs):
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.request(method, self.url + path, headers=self.headers(token, service), **kwargs)
        if response.status_code >= 400:
            raise HTTPException(response.status_code if response.status_code < 500 else 502, detail={"code":"SUPABASE_ERROR","message":response.text[:500]})
        return response
    async def rows(self, table: str, query: str = "", **kwargs):
        return (await self.request("GET", f"/rest/v1/{table}?{query}", **kwargs)).json()

db = Supabase()
app = FastAPI(title="PSI Shared Tool", docs_url=None, redoc_url=None)

def error(status: int, code: str, message: str, details: dict[str, Any] | None = None):
    raise HTTPException(status, detail={"code": code, "message": message, "details": details or {}})

@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) and "code" in exc.detail else {"code":"HTTP_ERROR","message":str(exc.detail),"details":{}}
    return Response(json.dumps({"error":detail}, ensure_ascii=False), exc.status_code, media_type="application/json")

async def actor(request: Request) -> dict[str, Any]:
    if not db.configured: error(503,"NOT_CONFIGURED","Supabase environment is not configured")
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token: error(401,"UNAUTHENTICATED","Login is required")
    user = (await db.request("GET","/auth/v1/user",token=token,service=False)).json()
    profiles = await db.rows("psi_profiles", f"user_id=eq.{user['id']}&select=login_id,team,display_name", token=token, service=False)
    if not profiles: error(403,"PROFILE_MISSING","This account is not provisioned")
    return {**profiles[0], "id": user["id"], "token": token}

def valid_week(week: str):
    if not re.fullmatch(r"20\d{2}-W(?:0[1-9]|[1-4]\d|5[0-3])", week): error(422,"INVALID_WEEK","Week must be YYYY-Www")

async def latest(week: str):
    return await db.rows("psi_latest_source_snapshots", f"reporting_week=eq.{week}&select=*&order=uploaded_at.desc")

async def generation(week: str):
    snapshots = await latest(week)
    selected = {x["source_type"]: x for x in snapshots}
    if set(selected) != set(REQUIRED_SOURCES): return None
    rules = await db.rows("psi_exclusion_rules", "active=eq.true&select=*")
    material = "|".join(selected[s]["checksum_sha256"] for s in REQUIRED_SOURCES) + json.dumps(rules, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(material.encode()).hexdigest()
    existing = await db.rows("psi_runs", f"reporting_week=eq.{week}&input_hash=eq.{digest}&status=eq.completed&select=*")
    if existing: return existing[0]
    run_id = str(uuid.uuid4())
    await db.request("POST","/rest/v1/psi_runs",json={"id":run_id,"reporting_week":week,"status":"processing","input_hash":digest,"rule_revision_hash":hashlib.sha256(json.dumps(rules,sort_keys=True).encode()).hexdigest(),"source_snapshot_ids":[x['id'] for x in selected.values()]},headers={**db.headers(),"Prefer":"return=representation"})
    try:
        files = {}
        manual_check_bytes: bytes | None = None
        for source, snapshot in selected.items():
            content = await db.request("GET", f"/storage/v1/object/psi-raw/{snapshot['storage_path']}")
            if source == "manual_check":
                manual_check_bytes = content.content
            else:
                files[snapshot["original_filename"]] = content.content
        if manual_check_bytes is None:
            raise ValueError("selected Manual Check control input is unavailable")
        result = build(files)
        year, week_number = week.split("-W")
        manual_check_as_of = date.fromisocalendar(int(year), int(week_number), 7)
        cases, suppressed_cases = reconcile_with_manual_check(result.issues, manual_check_bytes, manual_check_as_of)
        links = []
        for case in cases:
            previous = await db.rows("psi_mismatch_cases", f"fingerprint=eq.{case['fingerprint']}&select=id")
            payload = {**case, "last_seen_at": datetime.now(timezone.utc).isoformat()}
            if previous:
                mismatch_id, new = previous[0]["id"], False
                await db.request("PATCH", f"/rest/v1/psi_mismatch_cases?fingerprint=eq.{case['fingerprint']}",json=payload)
            else:
                response = await db.request("POST","/rest/v1/psi_mismatch_cases",json=payload,headers={**db.headers(),"Prefer":"return=representation"})
                mismatch_id, new = response.json()[0]["id"], True
            links.append({"run_id":run_id,"mismatch_id":mismatch_id,"is_new":new})
        if links: await db.request("POST","/rest/v1/psi_run_mismatches",json=links)
        path = f"{week}/{run_id}/PSI Final.xlsx"
        await db.request("POST", f"/storage/v1/object/psi-output/{path}", content=result.xlsx, headers={**db.headers(),"Content-Type":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","x-upsert":"true"})
        summary = dict(result.summary); summary.update({"mismatch_count":len(cases),"manual_check_suppressed_count":len(suppressed_cases),"excluded_rules":len(rules)})
        response = await db.request("PATCH",f"/rest/v1/psi_runs?id=eq.{run_id}",json={"status":"completed","output_path":path,"output_checksum_sha256":hashlib.sha256(result.xlsx).hexdigest(),"summary":summary,"completed_at":datetime.now(timezone.utc).isoformat()},headers={**db.headers(),"Prefer":"return=representation"})
        return response.json()[0]
    except Exception as exc:
        await db.request("PATCH",f"/rest/v1/psi_runs?id=eq.{run_id}",json={"status":"failed","error_message":str(exc)[:1000],"completed_at":datetime.now(timezone.utc).isoformat()})
        raise

@app.get("/health")
async def health(): return {"ok":True,"supabase_configured":db.configured}

@app.post("/api/auth/login")
async def login(payload: dict[str, str]):
    login_id, password = payload.get("user_id", "").strip().lower(), payload.get("password", "")
    email = LOGIN_EMAILS.get(login_id)
    if not email: error(401,"INVALID_LOGIN","Invalid user ID or password")
    response = await db.request("POST","/auth/v1/token?grant_type=password",service=False,json={"email":email,"password":password})
    session = response.json(); user = session["user"]
    profile = (await db.rows("psi_profiles", f"user_id=eq.{user['id']}&select=login_id,team,display_name", token=session["access_token"],service=False))[0]
    return {"access_token":session["access_token"],"expires_in":session.get("expires_in"),"profile":profile}

@app.get("/api/me")
async def me(user=Depends(actor)): return {k:user[k] for k in ("login_id","team","display_name")}

@app.get("/api/weeks/{week}/dashboard")
async def dashboard(week: str, user=Depends(actor)):
    valid_week(week); snapshots = await latest(week); by_source={x['source_type']:x for x in snapshots}
    runs=await db.rows("psi_runs",f"reporting_week=eq.{week}&select=*&order=created_at.desc&limit=1")
    mismatch=await db.rows("psi_mismatch_cases", "status=eq.open&select=id")
    return {"week":week,"viewer":{k:user[k] for k in ('login_id','team','display_name')},"sources":[{"source":s,"label":SOURCE_LABELS[s],"owner":SOURCE_OWNERS[s],"can_upload":may_upload(user['team'],s),"snapshot":by_source.get(s)} for s in REQUIRED_SOURCES],"ready":len(by_source)==len(REQUIRED_SOURCES),"latest_run":runs[0] if runs else None,"open_mismatch_count":len(mismatch)}

@app.post("/api/weeks/{week}/sources/{source}/upload")
async def upload(week: str, source: str, tasks: BackgroundTasks, file: UploadFile=File(...), data_as_of: str|None=Form(None), user=Depends(actor)):
    valid_week(week)
    if source not in REQUIRED_SOURCES: error(404,"SOURCE_UNKNOWN","Unknown source")
    if not may_upload(user['team'],source): error(403,"SOURCE_FORBIDDEN","Your team cannot upload this source")
    safe_name=Path(file.filename or "upload.xlsx").name
    content=await file.read()
    if not safe_name.lower().endswith(".xlsx") or not content.startswith(b"PK"): error(422,"FILE_INVALID","Only valid .xlsx files are accepted")
    if not content or len(content)>MAX_BYTES: error(422,"FILE_TOO_LARGE","File must be between 1 byte and 50 MB")
    try:
        if source == "manual_check": load_manual_check(content)
        else: build({safe_name:content})
    except Exception as exc: error(422,"SCHEMA_INVALID",str(exc))
    prior=await db.rows("psi_source_snapshots",f"reporting_week=eq.{week}&source_type=eq.{source}&select=version&order=version.desc&limit=1")
    version=(prior[0]['version'] if prior else 0)+1; snap_id=str(uuid.uuid4()); checksum=hashlib.sha256(content).hexdigest(); path=f"{user['team']}/{week}/{source}/{snap_id}.xlsx"
    await db.request("POST",f"/storage/v1/object/psi-raw/{path}",content=content,headers={**db.headers(),"Content-Type":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","x-upsert":"false"})
    row={"id":snap_id,"reporting_week":week,"source_type":source,"owner_team":user['team'],"version":version,"original_filename":safe_name,"storage_path":path,"checksum_sha256":checksum,"byte_size":len(content),"data_as_of":data_as_of,"schema_status":"passed","schema_details":{},"uploaded_by":user['id']}
    await db.request("POST","/rest/v1/psi_source_snapshots",json=row)
    if len(await latest(week)) == len(REQUIRED_SOURCES): tasks.add_task(generation,week)
    return {"snapshot":row,"generation_queued":len(await latest(week)) == len(REQUIRED_SOURCES)}

@app.get("/api/weeks/{week}/mismatches")
async def mismatches(week: str,status: str|None=None,new_only: bool=False,search: str="",user=Depends(actor)):
    valid_week(week); query=f"select=*,psi_run_mismatches!inner(run_id,is_new,psi_runs!inner(reporting_week))&psi_run_mismatches.psi_runs.reporting_week=eq.{week}"
    if status: query += f"&status=eq.{status}"
    rows=await db.rows("psi_mismatch_cases",query)
    return [x for x in rows if (not new_only or any(y.get('is_new') for y in x.get('psi_run_mismatches',[]))) and search.lower() in x.get('record_key','').lower()]

@app.patch("/api/mismatches/{mismatch_id}")
async def update_mismatch(mismatch_id: str,payload: dict[str,str],user=Depends(actor)):
    status=payload.get("status"); note=payload.get("note")
    if status and status not in {"open","handled","ignored","excluded"}: error(422,"STATUS_INVALID","Invalid status")
    data={k:v for k,v in {"status":status,"note":note}.items() if v is not None}
    if status=="handled": data.update({"handled_by":user['id'],"handled_at":datetime.now(timezone.utc).isoformat()})
    return (await db.request("PATCH",f"/rest/v1/psi_mismatch_cases?id=eq.{mismatch_id}",json=data,headers={**db.headers(),"Prefer":"return=representation"})).json()[0]

@app.post("/api/weeks/{week}/generate")
async def generate(week: str,tasks: BackgroundTasks,user=Depends(actor)):
    if user['team']!='tech': error(403,"TECH_REQUIRED","Only Tech can regenerate PSI")
    valid_week(week); tasks.add_task(generation,week); return {"queued":True}

@app.get("/api/runs/{run_id}/download")
async def download(run_id: str,user=Depends(actor)):
    rows=await db.rows("psi_runs",f"id=eq.{run_id}&status=eq.completed&select=output_path")
    if not rows: error(404,"RUN_NOT_FOUND","Completed run not found")
    response=await db.request("GET",f"/storage/v1/object/psi-output/{rows[0]['output_path']}")
    return Response(response.content,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":"attachment; filename=PSI Final.xlsx"})

# StaticFiles resolves paths under this directory; it cannot serve ../, .git, or process files.
app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
