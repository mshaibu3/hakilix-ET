from __future__ import annotations
import json, time, uuid
from datetime import datetime, timezone
from hashlib import sha256
from typing import Callable

import structlog
from hakilix.observability import init_logging, init_otel

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import text
from pydantic import BaseModel

from hakilix.config import settings
from hakilix.db import db_session
from hakilix.security import verify_password, create_access_token, decode_token
init_logging("hakilix-api")
init_otel("hakilix-api")
log = structlog.get_logger("hakilix-api")

from hakilix.schemas import Problem, TokenResponse, ResidentCreate, ResidentOut, RiskSummary, TelemetryIn

REQ_COUNT = Counter("hakilix_http_requests_total", "HTTP requests", ["method", "path", "status"])
REQ_LAT = Histogram("hakilix_http_request_seconds", "Request latency", ["path"])
bearer = HTTPBearer(auto_error=False)

def problem(status_code: int, title: str, code: str, detail: str | None = None) -> JSONResponse:
    p = Problem(title=title, status=status_code, code=code, detail=detail)
    return JSONResponse(status_code=status_code, content=p.model_dump())

def get_principal(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict | None:
    if not creds:
        return None
    token = creds.credentials
    # 1) Try Hakilix internal JWT (HS256) first
    try:
        return decode_token(token)
    except Exception:
        pass
    # 2) Optionally accept OIDC JWTs (RS256) using JWKS
    if settings.oidc_enabled:
        try:
            from hakilix.oidc import decode_oidc
            claims = decode_oidc(token, issuer=settings.oidc_issuer, audience=settings.oidc_audience, jwks_url=settings.oidc_jwks_url)
            # Map into Hakilix principal contract
            return {
                "sub": claims.get("sub"),
                "agency_id": claims.get("tenant") or claims.get("agency_id") or settings.demo_agency_id,
                "role": claims.get("role") or claims.get("roles", ["clinician"])[0] if isinstance(claims.get("roles"), list) else "clinician",
                "iss": claims.get("iss"),
                "aud": claims.get("aud"),
                "oidc": True,
            }
        except Exception:
            return None
    return None


def require_auth(principal: dict | None = Depends(get_principal)) -> dict:
    if not principal:
        raise HTTPException(status_code=401, detail="unauthorized")
    return principal

def require_role(allowed: set[str]):
    def _dep(principal: dict = Depends(require_auth)) -> dict:
        if principal.get("role") not in allowed:
            raise HTTPException(status_code=403, detail="forbidden")
        return principal
    return _dep

app = FastAPI(title="Hakilix API", version="1.0.0", redirect_slashes=False)

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
try:
    FastAPIInstrumentor.instrument_app(app)
except Exception:
    pass

@app.middleware("http")
async def request_mw(request: Request, call_next: Callable):
    rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    start = time.time()
    try:
        response: Response = await call_next(request)
    finally:
        dur = time.time() - start
        REQ_LAT.labels(path=request.url.path).observe(dur)
    response.headers["X-Request-Id"] = rid
    REQ_COUNT.labels(method=request.method, path=request.url.path, status=str(response.status_code)).inc()
    return response

@app.exception_handler(HTTPException)
async def http_exc(request: Request, exc: HTTPException):
    code = "http_error"
    if exc.status_code == 401: code = "unauthorized"
    if exc.status_code == 403: code = "forbidden"
    if exc.status_code == 404: code = "not_found"
    return problem(exc.status_code, "Request failed", code, str(exc.detail))

@app.get("/v1/health")
def health():
    return {"status":"ok","service":"hakilix_api","time": datetime.now(timezone.utc).isoformat()}

@app.get("/v1/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/v1/auth/token", response_model=TokenResponse)
def token(form: OAuth2PasswordRequestForm = Depends()):
    with db_session(tenant_id=settings.demo_agency_id) as db:
        row = db.execute(text("SELECT id, agency_id, password_hash, role FROM hakilix.users WHERE email=:e"), {"e": form.username}).mappings().first()
        if not row or not verify_password(row["password_hash"], form.password):
            raise HTTPException(status_code=401, detail="invalid_credentials")
        jwt_ = create_access_token(subject=row["id"], agency_id=row["agency_id"], role=row["role"])
        db.execute(text("INSERT INTO hakilix.audit_log(time, agency_id, actor_user_id, action, resource, resource_id, detail) VALUES (:t,:aid,:uid,'auth.login','user',:uid,:d)"),
                   {"t": datetime.now(timezone.utc), "aid": row["agency_id"], "uid": row["id"], "d": json.dumps({"email": form.username})})
        return TokenResponse(access_token=jwt_)

class LoginIn(BaseModel):
    email: str
    password: str

@app.post("/v1/auth/login", response_model=TokenResponse)
def login_json(payload: LoginIn):
    # Compatibility endpoint for dashboards/clients posting JSON.
    class _Form:
        def __init__(self, username: str, password: str):
            self.username = username
            self.password = password
    return token(_Form(username=payload.email, password=payload.password))


@app.get("/v1/residents", response_model=list[ResidentOut])
def list_residents(principal: dict = Depends(require_auth)):
    tid = principal["agency_id"]
    with db_session(tenant_id=tid) as db:
        rows = db.execute(text("SELECT id, agency_id, display_name, created_at FROM hakilix.residents ORDER BY id")).mappings().all()
        return [ResidentOut(**dict(r)) for r in rows]

@app.post("/v1/residents", response_model=ResidentOut)
def create_resident(payload: ResidentCreate, principal: dict = Depends(require_role({"agency_admin","clinician"}))):
    tid = principal["agency_id"]
    now = datetime.now(timezone.utc)
    with db_session(tenant_id=tid) as db:
        db.execute(text("INSERT INTO hakilix.residents(id, agency_id, display_name, created_at) VALUES (:id,:aid,:dn,:t) ON CONFLICT (id) DO UPDATE SET display_name=EXCLUDED.display_name"),
                   {"id": payload.id, "aid": tid, "dn": payload.display_name, "t": now})
        db.execute(text("INSERT INTO hakilix.audit_log(time, agency_id, actor_user_id, action, resource, resource_id, detail) VALUES (:t,:aid,:uid,'resident.upsert','resident',:rid,:d)"),
                   {"t": now, "aid": tid, "uid": principal["sub"], "rid": payload.id, "d": json.dumps(payload.model_dump())})
        row = db.execute(text("SELECT id, agency_id, display_name, created_at FROM hakilix.residents WHERE id=:id"), {"id": payload.id}).mappings().first()
        return ResidentOut(**dict(row))

@app.delete("/v1/residents/{resident_id}")
def delete_resident(resident_id: str, principal: dict = Depends(require_role({"agency_admin"}))):
    tid = principal["agency_id"]
    now = datetime.now(timezone.utc)
    with db_session(tenant_id=tid) as db:
        # Ensure resident exists under tenant. If not, return 404.
        exists = db.execute(text("SELECT id FROM hakilix.residents WHERE id=:id"), {"id": resident_id}).scalar()
        if not exists:
            raise HTTPException(status_code=404, detail="resident_not_found")

        # Safe cleanup before deletion:
        # - Unassign devices (FK safety)
        # - Remove resident-bound time-series rows (demo hygiene)
        # - Keep audit history but add a deletion audit entry with counts
        dev_cnt = db.execute(text("UPDATE hakilix.devices SET resident_id=NULL WHERE resident_id=:id"), {"id": resident_id}).rowcount or 0
        tel_cnt = db.execute(text("DELETE FROM hakilix.telemetry WHERE resident_id=:id"), {"id": resident_id}).rowcount or 0
        risk_cnt = db.execute(text("DELETE FROM hakilix.risk_events WHERE resident_id=:id"), {"id": resident_id}).rowcount or 0

        db.execute(text("DELETE FROM hakilix.residents WHERE id=:id"), {"id": resident_id})

        db.execute(
            text(
                "INSERT INTO hakilix.audit_log(time, agency_id, actor_user_id, action, resource, resource_id, detail) "
                "VALUES (:t,:aid,:uid,'resident.delete','resident',:rid,:d)"
            ),
            {
                "t": now,
                "aid": tid,
                "uid": principal["sub"],
                "rid": resident_id,
                "d": json.dumps({"devices_unassigned": dev_cnt, "telemetry_deleted": tel_cnt, "risk_events_deleted": risk_cnt}),
            },
        )
    return {"status":"deleted","resident_id":resident_id}

@app.post("/v1/telemetry/ingest")
def ingest_telemetry(payload: TelemetryIn, request: Request):
    dev_id = request.headers.get("X-Device-Id")
    token = request.headers.get("X-Device-Token")
    if not dev_id or not token:
        raise HTTPException(status_code=401, detail="device_auth_required")

    token_hash = sha256(token.encode("utf-8")).hexdigest()

    # Demo: device auth lives under demo tenant. For multi-tenant production, use mTLS
    # and/or an edge identity token that includes tenant context.
    with db_session(tenant_id=settings.demo_agency_id) as db:
        row = db.execute(
            text("SELECT id, agency_id, state, token_hash FROM hakilix.devices WHERE id=:id"),
            {"id": dev_id},
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=401, detail="unknown_device")
        if row["state"] not in ("active", "rotated"):
            raise HTTPException(status_code=403, detail="device_not_active")
        if row["token_hash"] != token_hash:
            raise HTTPException(status_code=401, detail="invalid_device_token")

        tid = row["agency_id"]

        # Route via broker if enabled (Cloud Run / Pub/Sub)
        if settings.broker_type.lower() == "pubsub":
            from hakilix.broker import get_broker
            broker = get_broker()
            if not settings.pubsub_topic:
                raise HTTPException(status_code=500, detail="pubsub_topic_not_configured")
            broker.publish(settings.pubsub_topic, {
                "agency_id": tid,
                "device_id": dev_id,
                "telemetry": payload.model_dump(mode="json"),
            })
            from hakilix.pipeline import audit
            audit(db, agency_id=tid, actor_device_id=dev_id, action="telemetry.queued", resource="resident", resource_id=payload.resident_id)
            return {"status": "queued"}

        # Direct persist
        db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tid})
        from hakilix.pipeline import persist_telemetry, audit
        persist_telemetry(db, agency_id=tid, t=payload)
        audit(db, agency_id=tid, actor_device_id=dev_id, action="telemetry.ingest", resource="resident", resource_id=payload.resident_id)
        return {"status": "ok"}



@app.get("/v1/residents/{resident_id}/latest", response_model=RiskSummary)
def latest_risk(resident_id: str, principal: dict = Depends(require_auth)):
    tid = principal["agency_id"]
    with db_session(tenant_id=tid) as db:
        row = db.execute(text("""
            SELECT time, resident_id, falls_risk, resp_risk, dehydration_risk, delirium_uti_risk, model_version, explain
            FROM hakilix.risk_events
            WHERE resident_id=:rid
            ORDER BY time DESC
            LIMIT 1
        """), {"rid": resident_id}).mappings().first()
        if not row: raise HTTPException(status_code=404, detail="no_risk_yet")
        return RiskSummary(**dict(row))

@app.get("/v1/telemetry/{resident_id}/recent")
def recent_telemetry(resident_id: str, principal: dict = Depends(require_auth), limit: int = 180):
    tid = principal["agency_id"]
    with db_session(tenant_id=tid) as db:
        rows = db.execute(text("""
            SELECT time, hr, spo2, rr, temp_c,
                   gait_instability, orthostatic_hypotension, night_wandering,
                   intake_ml, sleep_fragmentation, agitation, toileting_freq
            FROM hakilix.telemetry
            WHERE resident_id=:rid
            ORDER BY time DESC
            LIMIT :lim
        """), {"rid": resident_id, "lim": int(limit)}).mappings().all()
        return {"resident_id": resident_id, "points": [dict(r) for r in rows]}
