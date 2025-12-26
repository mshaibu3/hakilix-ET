from __future__ import annotations

import os
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from hakilix.secrets import resolve_secret

_DEFAULT_APP_URL = "postgresql+psycopg://hakilix_app:hakilix@timescaledb:5432/hakilix"
_DEFAULT_MIGRATOR_URL = "postgresql+psycopg://hakilix_migrator:hakilix@timescaledb:5432/hakilix"

class Settings(BaseSettings):
    # Compose passes env vars; env_file is optional (missing file is fine).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hakilix_env: str = "dev"
    hakilix_jwt_secret: str = "change-me-in-prod"
    hakilix_jwt_issuer: str = "hakilix"
    hakilix_jwt_audience: str = "hakilix-agency-portal"
    hakilix_access_token_minutes: int = 60

    # IMPORTANT: do NOT require these at import-time; use safe defaults.
    database_url_app: str = _DEFAULT_APP_URL
    database_url_migrator: Optional[str] = None
    redis_url: str = "redis://redis:6379/0"

    demo_agency_id: str = "A-001"
    demo_agency_name: str = "Hakilix Demo Agency"
    demo_admin_email: str = "admin@hakilix.local"
    demo_admin_password: str = "Admin!234"
    demo_resident_id: str = "R-001"
    demo_resident_name: str = "Resident One"
    demo_device_id: str = "D-001"

    # --- Cloud / security hardening ---
    oidc_enabled: bool = False
    oidc_issuer: str = "https://issuer.example"
    oidc_audience: str = "hakilix-api"
    oidc_jwks_url: str = "https://issuer.example/.well-known/jwks.json"

    broker_type: str = "direct"   # direct|pubsub
    pubsub_topic: str = ""        # projects/<p>/topics/<t>

    @field_validator("database_url_app", mode="before")
    @classmethod
    def _coerce_db_url_app(cls, v):
        # Accept multiple env naming conventions robustly.
        if v:
            return resolve_secret(str(v))
        for k in ("DATABASE_URL_APP", "HAKILIX_DATABASE_URL_APP", "DATABASE_URL"):
            if os.getenv(k):
                return resolve_secret(os.getenv(k))
        # As a last resort, construct from POSTGRES_* (for local dev).
        db = os.getenv("POSTGRES_DB", "hakilix")
        user = os.getenv("POSTGRES_USER_APP", "hakilix_app")
        pwd = os.getenv("POSTGRES_PASSWORD_APP", "hakilix")
        host = os.getenv("POSTGRES_HOST", "timescaledb")
        port = os.getenv("POSTGRES_PORT_INTERNAL", "5432")
        return f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"

    @field_validator("database_url_migrator", mode="before")
    @classmethod
    def _coerce_db_url_migrator(cls, v):
        if v:
            return resolve_secret(str(v))
        for k in ("DATABASE_URL_MIGRATOR", "HAKILIX_DATABASE_URL_MIGRATOR"):
            if os.getenv(k):
                return resolve_secret(os.getenv(k))
        # If not explicitly set, infer migrator URL from app URL.
        # Prefer the dedicated migrator role used by init scripts.
        app_url = os.getenv("DATABASE_URL_APP") or os.getenv("HAKILIX_DATABASE_URL_APP") or _DEFAULT_APP_URL
        if "hakilix_app:" in app_url:
            return app_url.replace("hakilix_app:", "hakilix_migrator:")
        return _DEFAULT_MIGRATOR_URL
@field_validator("hakilix_jwt_secret", mode="before")
@classmethod
def _coerce_jwt_secret(cls, v):
    # Accept Secret Manager ref: sm://projects/<p>/secrets/<s>/versions/<v>
    if v is None:
        return v
    return resolve_secret(str(v))


settings = Settings()
