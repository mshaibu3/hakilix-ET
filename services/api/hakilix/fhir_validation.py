from __future__ import annotations

import json
from typing import Any, Dict, Optional

import jsonschema

# A minimal Observation schema subset. Not full FHIR; intended for demo validation.
FHIR_OBSERVATION_SCHEMA: Dict[str, Any] = {
  "type":"object",
  "required":["resourceType","status","code","subject","effectiveDateTime"],
  "properties":{
    "resourceType":{"const":"Observation"},
    "status":{"type":"string"},
    "code":{"type":"object"},
    "subject":{"type":"object"},
    "effectiveDateTime":{"type":"string"},
    "valueQuantity":{"type":"object"},
    "component":{"type":"array"},
    "meta":{"type":"object"}
  }
}

def validate_observation(obs: Dict[str, Any]) -> None:
    jsonschema.validate(instance=obs, schema=FHIR_OBSERVATION_SCHEMA)

def build_observation_vitals(agency_id: str, resident_id: str, effective: str, hr: float|None, spo2: float|None, rr: float|None, temp_c: float|None) -> Dict[str, Any]:
    obs = {
        "resourceType":"Observation",
        "status":"final",
        "meta":{"profile":["https://hakilix.local/fhir/StructureDefinition/hakilix-vitals-observation"],"tag":[{"system":"https://hakilix.local/tenant","code":agency_id}]},
        "code":{"text":"Hakilix Vital Signs"},
        "subject":{"reference":f"Patient/{resident_id}"},
        "effectiveDateTime": effective,
        "component":[]
    }
    if hr is not None:
        obs["component"].append({"code":{"text":"Heart rate"},"valueQuantity":{"value":hr,"unit":"beats/min"}})
    if spo2 is not None:
        obs["component"].append({"code":{"text":"SpO2"},"valueQuantity":{"value":spo2,"unit":"%"}})
    if rr is not None:
        obs["component"].append({"code":{"text":"Respiratory rate"},"valueQuantity":{"value":rr,"unit":"breaths/min"}})
    if temp_c is not None:
        obs["component"].append({"code":{"text":"Temperature"},"valueQuantity":{"value":temp_c,"unit":"C"}})
    validate_observation(obs)
    return obs
