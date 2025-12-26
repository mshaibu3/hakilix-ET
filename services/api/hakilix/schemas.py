from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field

class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    code: str = "unknown_error"
    instance: str | None = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ResidentCreate(BaseModel):
    id: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=2, max_length=255)

class ResidentOut(BaseModel):
    id: str
    agency_id: str
    display_name: str
    created_at: datetime

class TelemetryIn(BaseModel):
    resident_id: str
    device_id: str
    time: datetime
    hr: float | None = None
    spo2: float | None = None
    rr: float | None = None
    temp_c: float | None = None
    gait_instability: float | None = None
    orthostatic_hypotension: float | None = None
    night_wandering: float | None = None
    intake_ml: float | None = None
    sleep_fragmentation: float | None = None
    agitation: float | None = None
    toileting_freq: float | None = None

class RiskSummary(BaseModel):
    time: datetime
    resident_id: str
    falls_risk: float
    resp_risk: float
    dehydration_risk: float
    delirium_uti_risk: float
    model_version: str
    explain: str | None = None
