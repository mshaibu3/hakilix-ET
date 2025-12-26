from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from hakilix.schemas import TelemetryIn

def persist_telemetry(db: Session, agency_id: str, t: TelemetryIn) -> None:
    db.execute(text("""
        INSERT INTO hakilix.telemetry
        (time, agency_id, resident_id, device_id, hr, spo2, rr, temp_c,
         gait_instability, orthostatic_hypotension, night_wandering, intake_ml,
         sleep_fragmentation, agitation, toileting_freq)
        VALUES
        (:time, :aid, :rid, :did, :hr, :spo2, :rr, :temp_c,
         :gait, :oh, :wander, :intake, :sleep, :agit, :toilet)
    """), {
        "time": t.time,
        "aid": agency_id,
        "rid": t.resident_id,
        "did": t.device_id,
        "hr": t.hr,
        "spo2": t.spo2,
        "rr": t.rr,
        "temp_c": t.temp_c,
        "gait": t.gait_instability,
        "oh": t.orthostatic_hypotension,
        "wander": t.night_wandering,
        "intake": t.intake_ml,
        "sleep": t.sleep_fragmentation,
        "agit": t.agitation,
        "toilet": t.toileting_freq,
    })

def audit(db: Session, agency_id: str, actor_device_id: str|None, action: str, resource: str, resource_id: str, detail: Dict[str,Any]|None=None) -> None:
    db.execute(text("""
        INSERT INTO hakilix.audit_log(time, agency_id, actor_device_id, action, resource, resource_id, detail)
        VALUES (:t,:aid,:did,:a,:r,:rid,:d)
    """), {
        "t": datetime.now(timezone.utc),
        "aid": agency_id,
        "did": actor_device_id,
        "a": action,
        "r": resource,
        "rid": resource_id,
        "d": json.dumps(detail) if detail else None
    })
