from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

import structlog
from fastapi import FastAPI, HTTPException, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis

log = structlog.get_logger("hakilix-worker")

DATABASE_URL = os.getenv("DATABASE_URL_INGEST") or os.getenv("DATABASE_URL_APP")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL_INGEST or DATABASE_URL_APP required")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STREAM = os.getenv("REDIS_STREAM", "hakilix.telemetry")

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

app = FastAPI(title="Hakilix Broker Worker", version="1.0.0")
try:
    FastAPIInstrumentor.instrument_app(app)
except Exception:
    pass

class PubSubMessage(BaseModel):
    message: Dict[str, Any]
    subscription: str | None = None

@app.get("/v1/health")
def health():
    return {"status":"ok","service":"hakilix_worker","time": datetime.now(timezone.utc).isoformat()}

def _decode_pubsub_data(msg: Dict[str, Any]) -> Dict[str, Any]:
    data_b64 = msg.get("data")
    if not data_b64:
        raise ValueError("missing_data")
    data = base64.b64decode(data_b64).decode("utf-8")
    return json.loads(data)

@app.post("/v1/pubsub/push")
async def pubsub_push(payload: PubSubMessage, request: Request):
    try:
        body = _decode_pubsub_data(payload.message)
    except Exception as e:
        log.warning("bad_pubsub_message", error=str(e))
        raise HTTPException(status_code=400, detail="bad_pubsub_message")

    agency_id = body.get("agency_id")
    device_id = body.get("device_id")
    telemetry = body.get("telemetry")
    if not agency_id or not telemetry:
        raise HTTPException(status_code=400, detail="missing_fields")

    # 1) persist telemetry
    with SessionLocal() as db:
        db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": agency_id})
        db.execute(text("""
            INSERT INTO hakilix.telemetry
            (time, agency_id, resident_id, device_id, hr, spo2, rr, temp_c,
             gait_instability, orthostatic_hypotension, night_wandering, intake_ml,
             sleep_fragmentation, agitation, toileting_freq)
            VALUES
            (:time,:aid,:rid,:did,:hr,:spo2,:rr,:temp_c,:gait,:oh,:wander,:intake,:sleep,:agit,:toilet)
        """), {
            "time": telemetry["time"],
            "aid": agency_id,
            "rid": telemetry["resident_id"],
            "did": telemetry.get("device_id", device_id),
            "hr": telemetry.get("hr"),
            "spo2": telemetry.get("spo2"),
            "rr": telemetry.get("rr"),
            "temp_c": telemetry.get("temp_c"),
            "gait": telemetry.get("gait_instability"),
            "oh": telemetry.get("orthostatic_hypotension"),
            "wander": telemetry.get("night_wandering"),
            "intake": telemetry.get("intake_ml"),
            "sleep": telemetry.get("sleep_fragmentation"),
            "agit": telemetry.get("agitation"),
            "toilet": telemetry.get("toileting_freq"),
        })
        db.execute(text("""
            INSERT INTO hakilix.audit_log(time, agency_id, actor_device_id, action, resource, resource_id, detail)
            VALUES (:t,:aid,:did,'telemetry.ingest','resident',:rid,NULL)
        """), {
            "t": telemetry["time"],
            "aid": agency_id,
            "did": device_id,
            "rid": telemetry["resident_id"],
        })
        db.commit()

    # 2) enqueue for inference worker via Redis stream
    r.xadd(STREAM, {"agency_id": agency_id, "resident_id": telemetry["resident_id"], "payload": json.dumps(telemetry)})

    return {"status":"ok"}
