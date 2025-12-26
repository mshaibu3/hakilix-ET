from __future__ import annotations
import os, time, json, random
from datetime import datetime, timezone
from hashlib import sha256
import requests, redis

API_BASE = os.environ.get("API_BASE", "http://hakilix-api:8080/v1")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
DEMO_DEVICE_ID = os.environ.get("DEMO_DEVICE_ID", "D-001")
DEMO_AGENCY_ID = os.environ.get("DEMO_AGENCY_ID", "A-001")
DEMO_RESIDENT_IDS = os.environ.get("DEMO_RESIDENT_IDS")

def _parse_residents() -> list[str]:
    if DEMO_RESIDENT_IDS:
        ids = [x.strip() for x in DEMO_RESIDENT_IDS.split(",") if x.strip()]
        if ids:
            return ids
    # Default: 10-demo fleet
    return [f"R-{i:03d}" for i in range(1, 11)]

RESIDENT_IDS = _parse_residents()

DEVICE_TOKEN = "devtok_" + sha256((DEMO_DEVICE_ID + DEMO_AGENCY_ID).encode("utf-8")).hexdigest()[:24]
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
STREAM = "hakilix.telemetry"

def gen(resident_id: str):
    base_hr = random.randint(62, 84)
    spo2 = round(random.uniform(95.0, 99.0), 1)
    rr = round(random.uniform(12.0, 18.0), 1)
    temp = round(random.uniform(36.2, 37.2), 2)

    gait = max(0.0, min(1.0, random.gauss(0.15, 0.08)))
    hypo = max(0.0, min(1.0, random.gauss(0.10, 0.06)))
    wander = max(0.0, min(1.0, random.gauss(0.10, 0.08)))

    if random.random() < 0.03: gait = min(1.0, gait + 0.55)
    if random.random() < 0.02: wander = min(1.0, wander + 0.65)
    if random.random() < 0.02: hypo = min(1.0, hypo + 0.60)

    intake = max(0.0, random.gauss(900.0, 200.0))
    if random.random() < 0.03: intake = max(0.0, intake - 700.0)

    sleep = max(0.0, min(1.0, random.gauss(0.15, 0.10)))
    agit = max(0.0, min(1.0, random.gauss(0.10, 0.10)))
    toilet = max(0.0, random.gauss(3.0, 1.2))
    if random.random() < 0.02:
        sleep = min(1.0, sleep + 0.65)
        agit = min(1.0, agit + 0.55)
        toilet = max(0.0, toilet + 5.0)

    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "resident_id": resident_id,
        "device_id": DEMO_DEVICE_ID,
        "hr": float(base_hr + random.gauss(0, 2)),
        "spo2": float(spo2),
        "rr": float(rr),
        "temp_c": float(temp),
        "gait_instability": float(gait),
        "orthostatic_hypotension": float(hypo),
        "night_wandering": float(wander),
        "intake_ml": float(intake),
        "sleep_fragmentation": float(sleep),
        "agitation": float(agit),
        "toileting_freq": float(toilet),
    }

def post(payload: dict):
    h = {"X-Device-Id": DEMO_DEVICE_ID, "X-Device-Token": DEVICE_TOKEN}
    r0 = requests.post(f"{API_BASE}/telemetry/ingest", json=payload, headers=h, timeout=5)
    if r0.status_code != 200:
        print("ingest failed", r0.status_code, r0.text)

def publish(resident_id: str, payload: dict):
    r.xadd(
        STREAM,
        {"agency_id": DEMO_AGENCY_ID, "resident_id": resident_id, "payload": json.dumps(payload)},
        maxlen=4000,
        approximate=True,
    )

def main():
    print("Telemetry simulator started.")
    i = 0
    while True:
        resident_id = RESIDENT_IDS[i % len(RESIDENT_IDS)]
        i += 1
        p = gen(resident_id)
        try:
            post(p)
            publish(resident_id, p)
        except Exception as e:
            print("telemetry sim error:", e)
        time.sleep(2)

if __name__ == "__main__":
    main()
