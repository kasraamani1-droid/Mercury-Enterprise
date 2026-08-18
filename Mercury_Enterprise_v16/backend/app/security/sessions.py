"""Shared session store — in-memory by default, Redis when REDIS_URL is set.

Enables multi-worker API deployments without sticky sessions.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Protocol

from ..core.config import settings

logger = logging.getLogger("mercury.security.sessions")

SESSION_KEY_PREFIX = "mercury:session:"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str):
        raw = value.replace("Z", "")
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return _utcnow()
    return _utcnow()


def _serialize(record: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def _deserialize(record: dict[str, Any]) -> dict[str, datetime | str]:
    out: dict[str, datetime | str] = {}
    for key, value in record.items():
        if key in {"created_at", "expires_at"}:
            out[key] = _parse_dt(value)
        else:
            out[key] = value
    return out


class SessionBackend(Protocol):
    def get(self, session_id: str) -> dict[str, datetime | str] | None: ...
    def set(self, session_id: str, record: dict[str, Any], ttl_seconds: int) -> None: ...
    def delete(self, session_id: str) -> None: ...
    def delete_for_operator(self, operator: str) -> int: ...
    def count(self) -> int: ...
    def cleanup_expired(self, now: datetime | None = None) -> int: ...
    @property
    def backend_name(self) -> str: ...


class MemorySessionBackend:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, datetime | str]] = {}

    @property
    def backend_name(self) -> str:
        return "memory"

    def get(self, session_id: str) -> dict[str, datetime | str] | None:
        record = self._sessions.get(session_id)
        if record is None:
            return None
        return dict(record)

    def set(self, session_id: str, record: dict[str, Any], ttl_seconds: int) -> None:
        _ = ttl_seconds
        self._sessions[session_id] = _deserialize(_serialize(record))

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def delete_for_operator(self, operator: str) -> int:
        name = (operator or "").strip()
        if not name:
            return 0
        victims = [
            sid
            for sid, record in self._sessions.items()
            if str(record.get("operator", "")) == name
        ]
        for sid in victims:
            self._sessions.pop(sid, None)
        return len(victims)

    def count(self) -> int:
        return len(self._sessions)

    def cleanup_expired(self, now: datetime | None = None) -> int:
        current = now or _utcnow()
        expired = [sid for sid, record in self._sessions.items() if _parse_dt(record["expires_at"]) <= current]
        for sid in expired:
            self._sessions.pop(sid, None)
        return len(expired)


class RedisSessionBackend:
    def __init__(self, redis_url: str) -> None:
        import redis  # type: ignore

        self._client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
        self._client.ping()

    @property
    def backend_name(self) -> str:
        return "redis"

    def _key(self, session_id: str) -> str:
        return f"{SESSION_KEY_PREFIX}{session_id}"

    def get(self, session_id: str) -> dict[str, datetime | str] | None:
        raw = self._client.get(self._key(session_id))
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.delete(session_id)
            return None
        if not isinstance(data, dict):
            return None
        return _deserialize(data)

    def set(self, session_id: str, record: dict[str, Any], ttl_seconds: int) -> None:
        payload = json.dumps(_serialize(record), separators=(",", ":"))
        ttl = max(1, int(ttl_seconds))
        self._client.setex(self._key(session_id), ttl, payload)

    def delete(self, session_id: str) -> None:
        self._client.delete(self._key(session_id))

    def delete_for_operator(self, operator: str) -> int:
        name = (operator or "").strip()
        if not name:
            return 0
        removed = 0
        for key in self._client.scan_iter(match=f"{SESSION_KEY_PREFIX}*", count=200):
            raw = self._client.get(key)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            if str(data.get("operator", "")) != name:
                continue
            self._client.delete(key)
            removed += 1
        return removed

    def count(self) -> int:
        count = 0
        for _ in self._client.scan_iter(match=f"{SESSION_KEY_PREFIX}*", count=200):
            count += 1
        return count

    def cleanup_expired(self, now: datetime | None = None) -> int:
        # Redis TTLs expire keys automatically.
        _ = now
        return 0


class SessionStore:
    """Facade used by the API process."""

    def __init__(self, backend: SessionBackend | None = None) -> None:
        self._backend = backend or self._build_backend()

    @staticmethod
    def _build_backend() -> SessionBackend:
        redis_url = (settings.redis_url or "").strip()
        if not redis_url:
            return MemorySessionBackend()
        try:
            backend = RedisSessionBackend(redis_url)
            logger.info("Session store backend=redis")
            return backend
        except Exception:
            if settings.redis_required:
                raise
            logger.exception("Redis session store unavailable; falling back to memory")
            return MemorySessionBackend()

    @property
    def backend_name(self) -> str:
        return self._backend.backend_name

    def get(self, session_id: str | None) -> dict[str, datetime | str] | None:
        if not session_id:
            return None
        record = self._backend.get(session_id)
        if record is None:
            return None
        if _parse_dt(record["expires_at"]) <= _utcnow():
            self._backend.delete(session_id)
            return None
        return record

    def save(self, session_id: str, record: dict[str, Any]) -> None:
        expires = _parse_dt(record.get("expires_at", _utcnow()))
        ttl = int((expires - _utcnow()).total_seconds())
        if ttl <= 0:
            self._backend.delete(session_id)
            return
        self._backend.set(session_id, record, ttl_seconds=ttl)

    def delete(self, session_id: str | None) -> None:
        if session_id:
            self._backend.delete(session_id)

    def delete_for_operator(self, operator: str) -> int:
        """Revoke every active session for an operator (password change / reset)."""
        return self._backend.delete_for_operator(operator)

    def count(self) -> int:
        return self._backend.count()

    def __len__(self) -> int:
        return self.count()

    def cleanup_expired(self, now: datetime | None = None) -> int:
        return self._backend.cleanup_expired(now)


session_store = SessionStore()
