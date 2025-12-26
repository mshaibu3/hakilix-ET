from __future__ import annotations
import os, json, time
from datetime import datetime, timezone
import redis
from sqlalchemy import create_engine, text
from inference.features import extract_features
from inference.model import RiskModel

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
DATABASE_URL_APP = os.environ.get("DATABASE_URL_APP")
if not DATABASE_URL_APP:
    raise SystemExit("DATABASE_URL_APP is required")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
eng = create_engine(DATABASE_URL_APP, future=True, pool_pre_ping=True)
model = RiskModel()

STREAM = "hakilix.telemetry"
GROUP = "inference"
CONSUMER = "worker-1"

def ensure_group():
    try:
        r.xgroup_create(STREAM, GROUP, id="0-0", mkstream=True)
    except Exception:
        pass

def insert_risk(agency_id: str, resident_id: str, scores: list[float]):
    now = datetime.now(timezone.utc)
    explain = json.dumps({
        "FALLS": "Gait / Hypotension / Wandering",
        "RESPIRATORY": "RR Trend / SpO₂ / Temp",
        "DEHYDRATION": "Intake / Tachycardia",
        "DELIRIUM_UTI": "Sleep / Agitation / Toileting",
    })
    with eng.begin() as c:
        c.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": agency_id})
        c.execute(text("""
            INSERT INTO hakilix.risk_events(time, agency_id, resident_id, falls_risk, resp_risk, dehydration_risk, delirium_uti_risk, model_version, explain)
            VALUES (:t,:aid,:rid,:f,:r,:d,:u,:mv,:e)
        """), {"t": now, "aid": agency_id, "rid": resident_id,
                  "f": scores[0], "r": scores[1], "d": scores[2], "u": scores[3],
                  "mv": model.version, "e": explain})

def main():
    ensure_group()
    print("Inference worker started.")
    while True:
        try:
            msgs = r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=50, block=5000)
            if not msgs:
                continue
            for _, entries in msgs:
                for msg_id, fields in entries:
                    agency_id = fields.get("agency_id", "A-001")
                    resident_id = fields.get("resident_id", "R-001")
                    payload = json.loads(fields.get("payload", "{}"))
                    fv = extract_features(payload)
                    scores = model.predict(fv.to_array())
                    insert_risk(agency_id, resident_id, scores)
                    r.xack(STREAM, GROUP, msg_id)
        except Exception as e:
            print("inference error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
