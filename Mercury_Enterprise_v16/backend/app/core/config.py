from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


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


OIDC_CALLBACK_PATH = "/api/v1/auth/oidc/callback"


def normalize_public_domain(domain: str) -> str:
    """Hostname only — strip accidental scheme/path from DOMAIN."""
    raw = (domain or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    host = (parsed.netloc or parsed.path.split("/")[0]).strip().lower()
    if "@" in host:
        host = host.rsplit("@", 1)[-1]
    return host.strip(".")


def expected_oidc_redirect_uri(domain: str) -> str:
    host = normalize_public_domain(domain)
    if not host:
        return ""
    return f"https://{host}{OIDC_CALLBACK_PATH}"


def _require_https_absolute_url(name: str, value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise RuntimeError(f"{name} must be set for production/HTTPS OIDC (no placeholder).")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(f"{name} must be an https:// URL (no http://, no relative path).")
    if parsed.username or parsed.password:
        raise RuntimeError(f"{name} must not embed credentials.")
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError(f"{name} must not use a loopback host for production OIDC.")
    return raw.rstrip("/")


FORBIDDEN_PASSWORDS = frozenset({"mercury-demo", "password", "admin", "changeme"})
DEV_PEPPER_FALLBACK = "mercury-dev-pepper"
FORBIDDEN_SECRETS = frozenset(
    {
        "",
        "changeme",
        "secret",
        "password",
        "jwt_secret",
        "cookie_secret",
        "mercury-demo",
        "insecure",
        "default",
        DEV_PEPPER_FALLBACK,
    }
)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("MERCURY_APP_NAME", "Mercury Enterprise API")
    version: str = os.getenv("MERCURY_VERSION", "16.0.0")
    environment: str = os.getenv("MERCURY_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./mercury.db")
    # QueuePool knobs apply to PostgreSQL only (SQLite ignores them in database.py).
    db_pool_size: int = _int("MERCURY_DB_POOL_SIZE", 5)
    db_max_overflow: int = _int("MERCURY_DB_MAX_OVERFLOW", 10)
    db_pool_recycle: int = _int("MERCURY_DB_POOL_RECYCLE", 1800)
    cors_origins: list[str] = None  # type: ignore[assignment]
    api_key: str = os.getenv("MERCURY_API_KEY", "")  # Optional machine auth via X-API-Key when set.
    seed_demo_data: bool = False
    auth_operator: str = os.getenv("MERCURY_AUTH_OPERATOR", "operator")
    auth_password: str = ""
    auth_mode: str = "password"
    require_oidc: bool = False
    allow_password_auth: bool = True
    password_login_enabled: bool = True
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = ""
    oidc_scopes: str = "openid profile email"
    oidc_username_claim: str = "preferred_username"
    oidc_discovery_url: str = ""
    oidc_jwks_uri: str = ""
    oidc_auto_provision: bool = False
    oidc_is_configured: bool = False
    oidc_jwks_cache_seconds: int = 300
    oidc_clock_skew_seconds: int = 60
    oidc_pkce_require_redis: bool = False
    sim_workspaces_visible: bool = True
    trusted_hosts: list[str] = None  # type: ignore[assignment]
    session_cookie_name: str = os.getenv("MERCURY_SESSION_COOKIE", "mercury_session")
    session_cookie_samesite: str = os.getenv("MERCURY_SESSION_SAMESITE", "lax")
    session_ttl_seconds: int = _int("MERCURY_SESSION_TTL_SECONDS", 3600)
    session_cookie_secure: bool = False
    audit_retention_days: int = _int("MERCURY_AUDIT_RETENTION_DAYS", 365)
    log_json: bool = _bool("MERCURY_LOG_JSON", False)
    metrics_enabled: bool = _bool("MERCURY_METRICS_ENABLED", True)
    jwt_secret: str = ""
    cookie_secret: str = ""
    domain: str = os.getenv("DOMAIN", "")
    https_enabled: bool = False
    letsencrypt_email: str = os.getenv("LETSENCRYPT_EMAIL", "")
    rate_limit_login_per_minute: int = _int("MERCURY_RATE_LIMIT_LOGIN_PER_MINUTE", 10)
    rate_limit_api_per_minute: int = _int("MERCURY_RATE_LIMIT_API_PER_MINUTE", 300)
    build_version: str = os.getenv("MERCURY_BUILD_VERSION", os.getenv("MERCURY_VERSION", "16.0.0"))
    redis_url: str = os.getenv("REDIS_URL", "")
    redis_required: bool = _bool("REDIS_REQUIRED", False)
    file_storage_root: str = os.getenv("MERCURY_FILE_STORAGE_ROOT", "")
    publications_storage_root: str = os.getenv("MERCURY_PUBLICATIONS_STORAGE_ROOT", "")
    audit_api_access: bool = _bool("MERCURY_AUDIT_API_ACCESS", False)
    log_file: str = os.getenv("LOG_FILE", "")
    argon2_time_cost: int = 2
    argon2_memory_kib: int = 19456
    argon2_parallelism: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "cors_origins", _csv("MERCURY_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"))
        # Never embed a demo/default password in the application binary/config defaults.
        object.__setattr__(self, "auth_password", os.getenv("MERCURY_AUTH_PASSWORD") or "")
        object.__setattr__(self, "jwt_secret", os.getenv("JWT_SECRET") or "")
        object.__setattr__(self, "cookie_secret", os.getenv("COOKIE_SECRET") or "")
        object.__setattr__(self, "https_enabled", _bool("HTTPS_ENABLED", False))
        object.__setattr__(self, "argon2_time_cost", _int("MERCURY_ARGON2_TIME_COST", 2))
        object.__setattr__(self, "argon2_memory_kib", _int("MERCURY_ARGON2_MEMORY_KIB", 19456))
        object.__setattr__(self, "argon2_parallelism", _int("MERCURY_ARGON2_PARALLELISM", 1))
        production = _is_production(self.environment)
        if os.getenv("MERCURY_SEED_DEMO") is None:
            object.__setattr__(self, "seed_demo_data", not production)
        else:
            object.__setattr__(self, "seed_demo_data", _bool("MERCURY_SEED_DEMO", not production))
        if os.getenv("MERCURY_REQUIRE_OIDC") is None:
            object.__setattr__(self, "require_oidc", bool(self.https_enabled))
        else:
            object.__setattr__(self, "require_oidc", _bool("MERCURY_REQUIRE_OIDC", False))
        mode = (os.getenv("MERCURY_AUTH_MODE") or ("oidc" if self.require_oidc else "password")).strip().lower()
        if mode not in {"password", "oidc"}:
            mode = "password"
        object.__setattr__(self, "auth_mode", mode)
        if os.getenv("MERCURY_ALLOW_PASSWORD_AUTH") is None:
            object.__setattr__(self, "allow_password_auth", not self.require_oidc)
        else:
            object.__setattr__(self, "allow_password_auth", _bool("MERCURY_ALLOW_PASSWORD_AUTH", False))
        object.__setattr__(
            self,
            "password_login_enabled",
            self.auth_mode == "password" or self.allow_password_auth,
        )
        object.__setattr__(self, "oidc_issuer", (os.getenv("MERCURY_OIDC_ISSUER") or "").strip())
        object.__setattr__(self, "oidc_client_id", (os.getenv("MERCURY_OIDC_CLIENT_ID") or "").strip())
        object.__setattr__(self, "oidc_client_secret", (os.getenv("MERCURY_OIDC_CLIENT_SECRET") or "").strip())
        object.__setattr__(self, "oidc_redirect_uri", (os.getenv("MERCURY_OIDC_REDIRECT_URI") or "").strip())
        object.__setattr__(self, "oidc_scopes", (os.getenv("MERCURY_OIDC_SCOPES") or "openid profile email").strip())
        object.__setattr__(
            self,
            "oidc_username_claim",
            (os.getenv("MERCURY_OIDC_USERNAME_CLAIM") or "preferred_username").strip() or "preferred_username",
        )
        object.__setattr__(self, "oidc_discovery_url", (os.getenv("MERCURY_OIDC_DISCOVERY_URL") or "").strip())
        object.__setattr__(self, "oidc_jwks_uri", (os.getenv("MERCURY_OIDC_JWKS_URI") or "").strip())
        object.__setattr__(self, "oidc_auto_provision", _bool("MERCURY_OIDC_AUTO_PROVISION", False))
        object.__setattr__(
            self,
            "oidc_is_configured",
            bool(self.oidc_issuer and self.oidc_client_id and self.oidc_client_secret and self.oidc_redirect_uri),
        )
        object.__setattr__(self, "oidc_jwks_cache_seconds", max(1, _int("MERCURY_OIDC_JWKS_CACHE_SECONDS", 300)))
        object.__setattr__(self, "oidc_clock_skew_seconds", max(0, _int("MERCURY_OIDC_CLOCK_SKEW_SECONDS", 60)))
        object.__setattr__(
            self,
            "oidc_pkce_require_redis",
            bool(
                self.redis_required
                or (
                    self.oidc_is_configured
                    and (production or self.https_enabled or self.require_oidc)
                )
            ),
        )
        if os.getenv("MERCURY_SIM_WORKSPACES") is None:
            object.__setattr__(self, "sim_workspaces_visible", not production)
        else:
            object.__setattr__(self, "sim_workspaces_visible", _bool("MERCURY_SIM_WORKSPACES", not production))
        hosts = _csv("MERCURY_TRUSTED_HOSTS", "")
        domain = (self.domain or "").strip()
        if domain and domain not in hosts:
            hosts.append(domain)
        object.__setattr__(self, "trusted_hosts", hosts)
        if self.https_enabled or production:
            # Production / HTTPS deployments never emit insecure session cookies.
            if os.getenv("MERCURY_SESSION_COOKIE_SECURE") is None:
                object.__setattr__(self, "session_cookie_secure", True)
            else:
                object.__setattr__(self, "session_cookie_secure", _bool("MERCURY_SESSION_COOKIE_SECURE", True))
            if self.https_enabled:
                object.__setattr__(self, "session_cookie_secure", True)
        else:
            if os.getenv("MERCURY_SESSION_COOKIE_SECURE") is None:
                object.__setattr__(self, "session_cookie_secure", False)
            else:
                object.__setattr__(self, "session_cookie_secure", _bool("MERCURY_SESSION_COOKIE_SECURE", False))
        samesite = (self.session_cookie_samesite or "lax").strip().lower()
        if samesite not in {"lax", "strict", "none"}:
            samesite = "lax"
        object.__setattr__(self, "session_cookie_samesite", samesite)

    def validate_for_startup(self) -> None:
        """Require an explicit operator password; forbid known demo/default secrets."""
        password = getattr(self, "auth_password", "") or ""
        https_enabled = bool(getattr(self, "https_enabled", False))
        production = _is_production(str(getattr(self, "environment", "development") or "development"))
        require_oidc = bool(getattr(self, "require_oidc", False))
        auth_mode = str(getattr(self, "auth_mode", "password") or "password").strip().lower()
        oidc_configured = bool(getattr(self, "oidc_is_configured", False))
        seed_demo = bool(getattr(self, "seed_demo_data", False))
        cors_origins = list(getattr(self, "cors_origins", []) or [])
        if not password:
            raise RuntimeError(
                "MERCURY_AUTH_PASSWORD must be set in the environment (no embedded demo default)."
            )
        if password.lower() in FORBIDDEN_PASSWORDS:
            raise RuntimeError("MERCURY_AUTH_PASSWORD uses a forbidden demo/default value; choose a unique secret.")
        if production and len(password) < 12:
            raise RuntimeError(
                "MERCURY_AUTH_PASSWORD must be at least 12 characters when MERCURY_ENV is production."
            )
        if production and seed_demo:
            raise RuntimeError(
                "MERCURY_SEED_DEMO must be false when MERCURY_ENV=production (refusing shared demo identities)."
            )
        if production or https_enabled:
            if not getattr(self, "session_cookie_secure", False):
                raise RuntimeError(
                    "Session cookies must be Secure when MERCURY_ENV=production or HTTPS_ENABLED=true "
                    "(refusing insecure cookies)."
                )
            self._validate_secret("JWT_SECRET", getattr(self, "jwt_secret", ""), minimum=32)
            self._validate_secret("COOKIE_SECRET", getattr(self, "cookie_secret", ""), minimum=32)
        if "*" in cors_origins:
            raise RuntimeError("MERCURY_CORS_ORIGINS must not include a wildcard when credentials are used.")
        if (production or https_enabled) and any(item.strip() == "*" for item in cors_origins):
            raise RuntimeError("Production CORS must not use a wildcard origin.")
        if https_enabled:
            for origin in cors_origins:
                if origin.startswith("http://") and "localhost" not in origin and "127.0.0.1" not in origin:
                    raise RuntimeError(
                        "HTTPS deployments must not allow non-local http:// CORS origins "
                        "(do not treat :3000 as the production public endpoint)."
                    )
                if ":3000" in origin:
                    raise RuntimeError(
                        "HTTPS deployments must not list :3000 in MERCURY_CORS_ORIGINS; "
                        "the production public endpoint is the TLS edge on :443."
                    )
            domain_host = normalize_public_domain(str(getattr(self, "domain", "") or ""))
            if domain_host:
                expected_origin = f"https://{domain_host}"
                origins_normalized = [item.strip().rstrip("/") for item in cors_origins]
                if expected_origin not in origins_normalized:
                    raise RuntimeError(
                        "MERCURY_CORS_ORIGINS must include https://$DOMAIN when HTTPS_ENABLED=true."
                    )
        if https_enabled and not (getattr(self, "domain", "") or "").strip():
            raise RuntimeError("DOMAIN must be set when HTTPS_ENABLED=true.")
        if https_enabled and not (getattr(self, "letsencrypt_email", "") or "").strip():
            raise RuntimeError("LETSENCRYPT_EMAIL must be set when HTTPS_ENABLED=true.")
        if require_oidc and auth_mode != "oidc":
            raise RuntimeError(
                "MERCURY_AUTH_MODE must be oidc when MERCURY_REQUIRE_OIDC=true or HTTPS_ENABLED=true "
                "(password demo auth is not internet production IAM)."
            )
        if require_oidc and not oidc_configured:
            raise RuntimeError(
                "OIDC is required for this deployment but is not fully configured. Set "
                "MERCURY_OIDC_ISSUER, MERCURY_OIDC_CLIENT_ID, MERCURY_OIDC_CLIENT_SECRET, and "
                "MERCURY_OIDC_REDIRECT_URI. Do not insert placeholder production credentials."
            )
        if auth_mode == "oidc" and not oidc_configured:
            raise RuntimeError(
                "MERCURY_AUTH_MODE=oidc requires MERCURY_OIDC_ISSUER, MERCURY_OIDC_CLIENT_ID, "
                "MERCURY_OIDC_CLIENT_SECRET, and MERCURY_OIDC_REDIRECT_URI."
            )
        production_oidc = oidc_configured and (production or https_enabled or require_oidc)
        if production_oidc:
            self._validate_production_oidc()
        if getattr(self, "redis_required", False) or production_oidc:
            redis_url = (getattr(self, "redis_url", "") or "").strip()
            reason = (
                "production OIDC PKCE/state is Redis-backed with no in-memory fallback"
                if production_oidc
                else "REDIS_REQUIRED=true"
            )
            if not redis_url:
                raise RuntimeError(f"REDIS_URL must be set ({reason}).")
            try:
                import redis  # type: ignore

                client = redis.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
                try:
                    client.ping()
                finally:
                    client.close()
            except RuntimeError:
                raise
            except Exception as exc:
                raise RuntimeError(f"Redis is required ({reason}) but unreachable at {redis_url}: {exc}") from exc

    def _validate_production_oidc(self) -> None:
        """Fail closed on production OIDC shape. Does not contact a live IdP."""
        domain = normalize_public_domain(str(getattr(self, "domain", "") or ""))
        if not domain:
            raise RuntimeError("DOMAIN must be set when production/HTTPS OIDC is configured.")
        issuer = _require_https_absolute_url(
            "MERCURY_OIDC_ISSUER", str(getattr(self, "oidc_issuer", "") or "")
        )
        client_id = str(getattr(self, "oidc_client_id", "") or "").strip()
        if not client_id:
            raise RuntimeError("MERCURY_OIDC_CLIENT_ID must be set for production OIDC.")
        redirect = str(getattr(self, "oidc_redirect_uri", "") or "").strip().rstrip("/")
        expected = expected_oidc_redirect_uri(domain)
        if redirect != expected.rstrip("/"):
            raise RuntimeError(
                "MERCURY_OIDC_REDIRECT_URI must match https://$DOMAIN/api/v1/auth/oidc/callback "
                "(no :3000, no http://, no invented path)."
            )
        _require_https_absolute_url(
            "MERCURY_OIDC_JWKS_URI", str(getattr(self, "oidc_jwks_uri", "") or "")
        )
        discovery = str(getattr(self, "oidc_discovery_url", "") or "").strip()
        if discovery:
            _require_https_absolute_url("MERCURY_OIDC_DISCOVERY_URL", discovery)
        issuer_host = (urlparse(issuer).hostname or "").lower()
        if issuer_host == domain:
            issuer_path = (urlparse(issuer).path or "").strip("/")
            if not issuer_path:
                raise RuntimeError(
                    "MERCURY_OIDC_ISSUER must be the IdP issuer URL, not the Mercury DOMAIN."
                )

    @staticmethod
    def _validate_secret(name: str, value: str, *, minimum: int) -> None:
        secret = (value or "").strip()
        if not secret:
            raise RuntimeError(f"{name} must be set for production/HTTPS deployments (no insecure default).")
        if secret.lower() in FORBIDDEN_SECRETS:
            raise RuntimeError(f"{name} uses a forbidden insecure default; choose a unique secret.")
        if len(secret) < minimum:
            raise RuntimeError(f"{name} must be at least {minimum} characters.")


settings = Settings()
