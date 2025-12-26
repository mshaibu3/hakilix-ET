from __future__ import annotations

import os
from typing import Optional

from cachetools import TTLCache

_cache = TTLCache(maxsize=256, ttl=300)

def _is_sm_ref(v: str) -> bool:
    return v.startswith("sm://")

def _parse_sm_ref(ref: str) -> tuple[str, str]:
    # sm://projects/<project>/secrets/<name>/versions/<version>
    parts = ref[len("sm://"):].split("/")
    try:
        proj_idx = parts.index("projects")
        secrets_idx = parts.index("secrets")
        versions_idx = parts.index("versions")
        project = parts[proj_idx+1]
        name = parts[secrets_idx+1]
        version = parts[versions_idx+1]
        return project, f"projects/{project}/secrets/{name}/versions/{version}"
    except Exception:
        raise ValueError("Invalid Secret Manager ref. Expected sm://projects/<p>/secrets/<s>/versions/<v>")

def resolve_secret(value_or_ref: Optional[str]) -> Optional[str]:
    if value_or_ref is None:
        return None
    v = value_or_ref.strip()
    if not v:
        return v
    if not _is_sm_ref(v):
        return v

    if v in _cache:
        return _cache[v]

    from google.cloud import secretmanager

    project, resource = _parse_sm_ref(v)
    client = secretmanager.SecretManagerServiceClient()
    resp = client.access_secret_version(name=resource)
    secret = resp.payload.data.decode("utf-8")
    _cache[v] = secret
    return secret
