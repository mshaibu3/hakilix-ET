from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from argon2 import PasswordHasher
from jose import jwt
from hakilix.config import settings

ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16)

def hash_password(pw: str) -> str:
    return ph.hash(pw)

def verify_password(hash_: str, pw: str) -> bool:
    try:
        ph.verify(hash_, pw)
        return True
    except Exception:
        return False

def create_access_token(subject: str, agency_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=int(settings.hakilix_access_token_minutes))
    payload: Dict[str, Any] = {
        "iss": settings.hakilix_jwt_issuer,
        "aud": settings.hakilix_jwt_audience,
        "sub": subject,
        "agency_id": agency_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.hakilix_jwt_secret, algorithm="HS256")

def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token,
        settings.hakilix_jwt_secret,
        algorithms=["HS256"],
        audience=settings.hakilix_jwt_audience,
        issuer=settings.hakilix_jwt_issuer,
    )
