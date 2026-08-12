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


def _is_production(environment: str) -> bool:
    return environment.strip().lower() in {"production", "prod"}


FORBIDDEN_PASSWORDS = frozenset({"mercury-demo", "password", "admin", "changeme"})


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("MERCURY_APP_NAME", "Mercury Enterprise API")
    version: str = os.getenv("MERCURY_VERSION", "16.0.0")
    environment: str = os.getenv("MERCURY_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./mercury.db")
    cors_origins: list[str] = None  # type: ignore[assignment]
    api_key: str = os.getenv("MERCURY_API_KEY", "")  # Reserved; not enforced by routes (session RBAC is primary).
    seed_demo_data: bool = os.getenv("MERCURY_SEED_DEMO", "true").lower() == "true"
    auth_operator: str = os.getenv("MERCURY_AUTH_OPERATOR", "operator")
    auth_password: str = ""
    session_cookie_name: str = os.getenv("MERCURY_SESSION_COOKIE", "mercury_session")
    session_cookie_samesite: str = os.getenv("MERCURY_SESSION_SAMESITE", "lax")
    session_ttl_seconds: int = _int("MERCURY_SESSION_TTL_SECONDS", 3600)
    session_cookie_secure: bool = False
    audit_retention_days: int = _int("MERCURY_AUDIT_RETENTION_DAYS", 365)
    log_json: bool = _bool("MERCURY_LOG_JSON", False)
    metrics_enabled: bool = _bool("MERCURY_METRICS_ENABLED", False)  # Reserved; /metrics not enabled by default.

    def __post_init__(self) -> None:
        object.__setattr__(self, "cors_origins", _csv("MERCURY_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"))
        # Never embed a demo/default password in the application binary/config defaults.
        object.__setattr__(self, "auth_password", os.getenv("MERCURY_AUTH_PASSWORD") or "")
        production = _is_production(self.environment)
        if os.getenv("MERCURY_SESSION_COOKIE_SECURE") is None:
            object.__setattr__(self, "session_cookie_secure", production)
        else:
            object.__setattr__(self, "session_cookie_secure", _bool("MERCURY_SESSION_COOKIE_SECURE", False))

    def validate_for_startup(self) -> None:
        """Require an explicit operator password; forbid known demo/default secrets."""
        password = self.auth_password or ""
        if not password:
            raise RuntimeError(
                "MERCURY_AUTH_PASSWORD must be set in the environment (no embedded demo default)."
            )
        if password.lower() in FORBIDDEN_PASSWORDS:
            raise RuntimeError("MERCURY_AUTH_PASSWORD uses a forbidden demo/default value; choose a unique secret.")
        if _is_production(self.environment) and len(password) < 12:
            raise RuntimeError(
                "MERCURY_AUTH_PASSWORD must be at least 12 characters when MERCURY_ENV is production."
            )


settings = Settings()
