"""Machine API-key authentication (optional alternative to session cookies).

When MERCURY_API_KEY is empty, behavior is unchanged (session-only).
When set, matching X-API-Key or Authorization: Bearer <key> authenticates a
service principal scoped to MERCURY_API_KEY_ORG_ID.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request

from ..core.config import settings

# Reserved login-directory name for machine principals (not a human operator).
MACHINE_OPERATOR = "api-key"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def configured_machine_org_id() -> str:
    return (os.getenv("MERCURY_API_KEY_ORG_ID") or "org-aviation-east").strip()


def configured_machine_site_id() -> str:
    return (os.getenv("MERCURY_API_KEY_SITE_ID") or "site-cyul").strip()


def configured_machine_role() -> str:
    return (os.getenv("MERCURY_API_KEY_ROLE") or "Operator").strip() or "Operator"


def api_key_configured() -> bool:
    return bool((settings.api_key or "").strip())


def extract_api_key(request: Request) -> str | None:
    header = request.headers.get("x-api-key")
    if header and header.strip():
        return header.strip()
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token or None
    return None


def api_key_matches(provided: str | None) -> bool:
    expected = (settings.api_key or "").strip()
    if not expected or not provided:
        return False
    if len(provided) != len(expected):
        # Still compare to reduce trivial timing leaks on length (best-effort).
        secrets.compare_digest(provided, provided)
        return False
    return secrets.compare_digest(provided, expected)


def machine_session() -> dict[str, datetime | str]:
    now = _utcnow()
    return {
        "operator": MACHINE_OPERATOR,
        "role": configured_machine_role(),
        "organization_id": configured_machine_org_id(),
        "site_id": configured_machine_site_id(),
        "created_at": now,
        "expires_at": now + timedelta(seconds=max(60, settings.session_ttl_seconds)),
        "auth_method": "api_key",
    }


def resolve_api_key_session(request: Request) -> dict[str, datetime | str] | None:
    if not api_key_configured():
        return None
    provided = extract_api_key(request)
    if not api_key_matches(provided):
        return None
    return machine_session()
