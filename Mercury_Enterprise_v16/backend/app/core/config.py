from __future__ import annotations

import os
from dataclasses import dataclass


def _csv(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("MERCURY_APP_NAME", "Mercury Enterprise API")
    version: str = os.getenv("MERCURY_VERSION", "16.0.0")
    environment: str = os.getenv("MERCURY_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./mercury.db")
    cors_origins: list[str] = None  # type: ignore[assignment]
    api_key: str = os.getenv("MERCURY_API_KEY", "")
    seed_demo_data: bool = os.getenv("MERCURY_SEED_DEMO", "true").lower() == "true"
    auth_operator: str = os.getenv("MERCURY_AUTH_OPERATOR", "operator")
    auth_password: str = os.getenv("MERCURY_AUTH_PASSWORD", "mercury-demo")
    session_cookie_name: str = os.getenv("MERCURY_SESSION_COOKIE", "mercury_session")
    session_cookie_samesite: str = os.getenv("MERCURY_SESSION_SAMESITE", "lax")
    session_ttl_seconds: int = _int("MERCURY_SESSION_TTL_SECONDS", 3600)
    session_cookie_secure: bool = _bool("MERCURY_SESSION_COOKIE_SECURE", False)
    audit_retention_days: int = _int("MERCURY_AUDIT_RETENTION_DAYS", 365)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cors_origins", _csv("MERCURY_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"))


settings = Settings()
