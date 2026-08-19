"""OIDC PKCE/state store — Redis when available, memory only for non-production.

Production / HTTPS / required OIDC: Redis only. No in-memory fallback.
Consume is single-use (GETDEL / pop) so replays fail closed.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Protocol

from fastapi import HTTPException, status

from ..core.config import settings

logger = logging.getLogger("mercury.security.oidc_pending")

PENDING_TTL_SECONDS = 600
PENDING_KEY_PREFIX = "mercury:oidc:pkce:"


class PendingStore(Protocol):
    def save(self, state: str, record: dict[str, Any], ttl_seconds: int = PENDING_TTL_SECONDS) -> None: ...
    def consume(self, state: str) -> dict[str, Any] | None: ...
    def clear(self) -> None: ...
    @property
    def backend_name(self) -> str: ...


class MemoryPendingStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, tuple[dict[str, Any], float]] = {}

    @property
    def backend_name(self) -> str:
        return "memory"

    def save(self, state: str, record: dict[str, Any], ttl_seconds: int = PENDING_TTL_SECONDS) -> None:
        expires = time.monotonic() + max(1, int(ttl_seconds))
        with self._lock:
            self._items[state] = (dict(record), expires)

    def consume(self, state: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._items.pop(state, None)
        if entry is None:
            return None
        record, expires = entry
        if expires <= time.monotonic():
            return None
        return record

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class RedisPendingStore:
    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_url(cls, redis_url: str) -> RedisPendingStore:
        import redis  # type: ignore

        client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        return cls(client)

    @property
    def backend_name(self) -> str:
        return "redis"

    def _key(self, state: str) -> str:
        return f"{PENDING_KEY_PREFIX}{state}"

    def save(self, state: str, record: dict[str, Any], ttl_seconds: int = PENDING_TTL_SECONDS) -> None:
        payload = json.dumps(record, separators=(",", ":"))
        ttl = max(1, int(ttl_seconds))
        try:
            self._client.setex(self._key(state), ttl, payload)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("OIDC PKCE Redis SET failed")
            raise _unavailable() from exc

    def consume(self, state: str) -> dict[str, Any] | None:
        key = self._key(state)
        try:
            getter = getattr(self._client, "getdel", None)
            if callable(getter):
                raw = getter(key)
            else:
                raw = self._client.get(key)
                if raw is not None:
                    self._client.delete(key)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("OIDC PKCE Redis GETDEL failed")
            raise _unavailable() from exc
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        return data

    def clear(self) -> None:
        for key in self._client.scan_iter(match=f"{PENDING_KEY_PREFIX}*", count=200):
            self._client.delete(key)


def pkce_requires_redis() -> bool:
    return bool(getattr(settings, "oidc_pkce_require_redis", False))


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="OIDC state store unavailable",
    )


def build_pending_store() -> PendingStore:
    redis_url = (settings.redis_url or "").strip()
    require_redis = pkce_requires_redis()
    if redis_url:
        try:
            store = RedisPendingStore.from_url(redis_url)
            logger.info("OIDC PKCE store backend=redis")
            return store
        except Exception as exc:
            if require_redis:
                logger.exception("OIDC PKCE Redis unavailable (fail closed)")
                raise _unavailable() from exc
            logger.exception("OIDC PKCE Redis unavailable; falling back to memory")
            return MemoryPendingStore()
    if require_redis:
        logger.error("OIDC PKCE requires Redis but REDIS_URL is empty")
        raise _unavailable()
    return MemoryPendingStore()
