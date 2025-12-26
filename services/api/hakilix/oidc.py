from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

import requests
from cachetools import TTLCache
from jose import jwt

_jwks_cache = TTLCache(maxsize=16, ttl=600)

def _get_jwks(jwks_url: str) -> Dict[str, Any]:
    if jwks_url in _jwks_cache:
        return _jwks_cache[jwks_url]
    r = requests.get(jwks_url, timeout=5)
    r.raise_for_status()
    data = r.json()
    _jwks_cache[jwks_url] = data
    return data

def decode_oidc(token: str, issuer: str, audience: str, jwks_url: str) -> Dict[str, Any]:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    jwks = _get_jwks(jwks_url)
    key = None
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            key = k
            break
    if key is None:
        # fallback: try first key
        keys = jwks.get("keys", [])
        if not keys:
            raise ValueError("jwks_empty")
        key = keys[0]
    return jwt.decode(token, key, algorithms=[header.get("alg","RS256")], issuer=issuer, audience=audience)
