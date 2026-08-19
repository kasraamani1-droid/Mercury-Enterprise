from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """Simple in-process sliding-window limiter (single-worker deployments)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: float = 60.0) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = SlidingWindowRateLimiter()


def client_key(request_client_host: str | None, forwarded_for: str | None) -> str:
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    return request_client_host or "unknown"


def is_probe_path(path: str) -> bool:
    return path in {
        "/health",
        "/ready",
        "/live",
        "/metrics",
        "/api/v1/health",
        "/api/v1/ready",
    }


def classify_rate_limit_path(path: str) -> str | None:
    """Return 'login', 'api', or None (unlimited)."""
    if is_probe_path(path):
        return None
    if path in {
        "/login",
        "/api/v1/auth/login",
        "/api/v1/auth/oidc/login",
        "/api/v1/auth/oidc/callback",
    } or "/auth/oidc/" in path:
        return "login"
    if path.startswith("/api"):
        return "api"
    return None
