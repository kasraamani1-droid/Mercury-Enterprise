from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any

from ..core.config import settings


class RateLimitStoreUnavailable(Exception):
    """Raised when Redis-backed limits are required but the store cannot be used."""


REDIS_KEY_PREFIX = "mercury:ratelimit:"


class SlidingWindowRateLimiter:
    """In-process sliding-window limiter (single-worker / LAN fallback)."""

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


class RedisFixedWindowRateLimiter:
    """Fixed-window limiter shared across uvicorn workers via Redis INCR.

    Production overlay runs --workers 2 with REDIS_REQUIRED=true. In-process
    sliding windows would not share counters between workers.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def allow(self, key: str, limit: int, window_seconds: float = 60.0) -> bool:
        if limit <= 0:
            return True
        redis_key = f"{REDIS_KEY_PREFIX}{key}"
        ttl = max(1, int(window_seconds))
        try:
            count = int(self._client.incr(redis_key))
            if count == 1:
                self._client.expire(redis_key, ttl)
            elif self._client.ttl(redis_key) in (-1, None):
                self._client.expire(redis_key, ttl)
            return count <= limit
        except Exception as exc:
            raise RateLimitStoreUnavailable("Redis rate-limit store unavailable") from exc

    def reset(self) -> None:
        try:
            for key in self._client.scan_iter(match=f"{REDIS_KEY_PREFIX}*", count=200):
                self._client.delete(key)
        except Exception as exc:
            raise RateLimitStoreUnavailable("Redis rate-limit store unavailable") from exc


class CompositeRateLimiter:
    """Redis when attached or REDIS_URL is usable; otherwise in-process memory."""

    def __init__(self) -> None:
        self._memory = SlidingWindowRateLimiter()
        self._redis: RedisFixedWindowRateLimiter | None = None
        self._lock = threading.Lock()

    def attach_redis(self, client: Any) -> None:
        with self._lock:
            self._redis = RedisFixedWindowRateLimiter(client)

    def detach_redis(self) -> None:
        with self._lock:
            self._redis = None

    @property
    def backend_name(self) -> str:
        return "redis" if self._redis is not None else "memory"

    def _ensure_redis(self) -> RedisFixedWindowRateLimiter | None:
        with self._lock:
            if self._redis is not None:
                return self._redis
            redis_url = (getattr(settings, "redis_url", "") or "").strip()
            require = bool(getattr(settings, "redis_required", False))
            if not redis_url:
                if require:
                    raise RateLimitStoreUnavailable("REDIS_URL is required for production rate limits")
                return None
            try:
                import redis  # type: ignore

                client = redis.Redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                )
                self._redis = RedisFixedWindowRateLimiter(client)
                return self._redis
            except RateLimitStoreUnavailable:
                raise
            except Exception as exc:
                if require:
                    raise RateLimitStoreUnavailable("Redis rate-limit store unavailable") from exc
                return None

    def allow(self, key: str, limit: int, window_seconds: float = 60.0) -> bool:
        require = bool(getattr(settings, "redis_required", False))
        try:
            backend = self._ensure_redis()
        except RateLimitStoreUnavailable:
            raise
        except Exception as exc:
            if require:
                raise RateLimitStoreUnavailable("Redis rate-limit store unavailable") from exc
            backend = None
        if backend is None:
            return self._memory.allow(key, limit, window_seconds)
        try:
            return backend.allow(key, limit, window_seconds)
        except RateLimitStoreUnavailable:
            if require:
                raise
            return self._memory.allow(key, limit, window_seconds)
        except Exception as exc:
            if require:
                raise RateLimitStoreUnavailable("Redis rate-limit store unavailable") from exc
            return self._memory.allow(key, limit, window_seconds)

    def reset(self) -> None:
        self._memory.reset()
        with self._lock:
            redis_backend = self._redis
        if redis_backend is not None:
            try:
                redis_backend.reset()
            except RateLimitStoreUnavailable:
                if bool(getattr(settings, "redis_required", False)):
                    raise


rate_limiter = CompositeRateLimiter()


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
