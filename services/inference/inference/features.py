from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class FeatureVector:
    hr: float
    spo2: float
    rr: float
    temp_c: float
    gait_instability: float
    orthostatic_hypotension: float
    night_wandering: float
    intake_ml: float
    sleep_fragmentation: float
    agitation: float
    toileting_freq: float

    def to_array(self):
        return [self.hr, self.spo2, self.rr, self.temp_c,
                self.gait_instability, self.orthostatic_hypotension, self.night_wandering,
                self.intake_ml, self.sleep_fragmentation, self.agitation, self.toileting_freq]

def _norm(x: float | None, lo: float, hi: float) -> float:
    if x is None:
        return 0.0
    v = (x - lo) / (hi - lo) if hi > lo else 0.0
    return max(0.0, min(1.0, float(v)))

def extract_features(t: Dict[str, Any]) -> FeatureVector:
    hr = _norm(t.get("hr", 75.0), 45.0, 140.0)
    spo2 = 1.0 - _norm(t.get("spo2", 98.0), 88.0, 100.0)
    rr = _norm(t.get("rr", 16.0), 8.0, 30.0)
    temp = _norm(t.get("temp_c", 36.7), 35.0, 39.5)

    gait = _norm(t.get("gait_instability", 0.2), 0.0, 1.0)
    hypo = _norm(t.get("orthostatic_hypotension", 0.2), 0.0, 1.0)
    wander = _norm(t.get("night_wandering", 0.1), 0.0, 1.0)

    intake = 1.0 - _norm(t.get("intake_ml", 800.0), 0.0, 2000.0)
    sleep = _norm(t.get("sleep_fragmentation", 0.2), 0.0, 1.0)
    agit = _norm(t.get("agitation", 0.2), 0.0, 1.0)
    toilet = _norm(t.get("toileting_freq", 3.0), 0.0, 10.0)

    return FeatureVector(hr, spo2, rr, temp, gait, hypo, wander, intake, sleep, agit, toilet)
