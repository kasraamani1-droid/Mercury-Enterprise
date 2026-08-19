"""SameSite=Lax is the primary CSRF control. Origin is checked when present."""

from __future__ import annotations

from urllib.parse import urlparse

from starlette.requests import Request

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "testserver", "::1"})


def _origin_from_referer(referer: str) -> str:
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def request_origin(request: Request) -> str:
    origin = (request.headers.get("origin") or "").strip()
    if origin and origin.lower() != "null":
        return origin
    referer = (request.headers.get("referer") or "").strip()
    if referer:
        return _origin_from_referer(referer)
    return ""


def origin_is_allowed(
    origin: str,
    *,
    cors_origins: list[str],
    domain: str = "",
) -> bool:
    if not origin:
        return True
    parsed = urlparse(origin)
    host = (parsed.hostname or "").lower()
    if host in _LOCAL_HOSTS:
        return True
    allowed = {item.strip().rstrip("/") for item in cors_origins if item.strip()}
    normalized = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if normalized in allowed:
        return True
    domain_host = (domain or "").strip().lower()
    if domain_host and host == domain_host:
        return True
    return False


def csrf_blocked(request: Request, *, cors_origins: list[str], domain: str = "") -> bool:
    if request.method.upper() in SAFE_METHODS:
        return False
    origin = request_origin(request)
    if not origin:
        return False
    return not origin_is_allowed(origin, cors_origins=cors_origins, domain=domain)
