"""Log and audit redaction — never persist passwords, tokens, or secrets."""

from __future__ import annotations

import re

_REDACT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(password[s]?|passwd|pwd)\s*[=:]\s*([^\s&\"']+)"),
    re.compile(r"(?i)(authorization)\s*[=:]\s*(?:bearer\s+)?([^\s&\"']+)"),
    re.compile(r"(?i)\b(bearer)\s+([A-Za-z0-9._\-+=/]+)"),
    re.compile(r"(?i)(cookie)\s*[=:]\s*([^\s;]+)"),
    re.compile(r"(?i)(mercury_session)=([^\s;]+)"),
    re.compile(r"(?i)(jwt_secret|cookie_secret|client_secret|api_key|token)\s*[=:]\s*([^\s&\"']+)"),
    re.compile(r"(?i)(code_verifier|refresh_token|id_token|access_token)\s*[=:]\s*([^\s&\"']+)"),
    re.compile(r"(?i)([?&](?:code|client_secret|access_token|id_token|refresh_token))=([^&\s]+)"),
    re.compile(r"(?i)(postgres_password|database_url)\s*[=:]\s*([^\s&\"']+)"),
)


def redact_text(value: str | None) -> str:
    text = str(value or "")
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}=***", text)
    return text


def is_sensitive_key(name: str | None) -> bool:
    key = (name or "").strip().lower()
    return key in {
        "password",
        "passwd",
        "authorization",
        "cookie",
        "jwt_secret",
        "cookie_secret",
        "client_secret",
        "api_key",
        "access_token",
        "refresh_token",
        "id_token",
        "code_verifier",
        "session_id",
        "mercury_session",
    }
