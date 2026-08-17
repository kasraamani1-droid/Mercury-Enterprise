from __future__ import annotations

import os
import shutil
import time
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.models import ConnectorState
from .config import settings
from . import metrics as metrics_mod


def check_database(db: Session) -> dict[str, str]:
    started = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        metrics_mod.observe_db_latency(time.perf_counter() - started)
        return {"database": "ok"}
    except Exception:
        metrics_mod.observe_db_latency(time.perf_counter() - started)
        return {"database": "error"}


def check_redis() -> dict[str, str]:
    redis_url = (os.getenv("REDIS_URL") or settings.redis_url or "").strip()
    if not redis_url:
        return {"redis": "not_configured"}
    client = None
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return {"redis": "ok"}
    except Exception:
        return {"redis": "error"}
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def check_disk(path: str | None = None) -> dict[str, Any]:
    target = path or os.getcwd()
    try:
        usage = shutil.disk_usage(target)
        free_percent = (usage.free / usage.total) * 100 if usage.total else 0.0
        status_value = "ok" if free_percent >= 10 else "degraded"
        return {
            "disk": status_value,
            "disk_free_percent": round(free_percent, 2),
            "disk_total_bytes": usage.total,
            "disk_free_bytes": usage.free,
        }
    except Exception:
        return {"disk": "error"}


def check_memory() -> dict[str, Any]:
    """Best-effort memory check (Linux /proc or psutil if present)."""
    try:
        import psutil  # type: ignore

        mem = psutil.virtual_memory()
        used_percent = float(mem.percent)
        status_value = "ok" if used_percent < 90 else "degraded"
        return {
            "memory": status_value,
            "memory_used_percent": round(used_percent, 2),
            "memory_total_bytes": int(mem.total),
            "memory_available_bytes": int(mem.available),
        }
    except Exception:
        pass
    try:
        # Linux fallback without extra dependency.
        meminfo: dict[str, int] = {}
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                parts = line.split(":")
                if len(parts) != 2:
                    continue
                key = parts[0].strip()
                value = parts[1].strip().split()[0]
                meminfo[key] = int(value) * 1024
        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        if total <= 0:
            return {"memory": "unknown"}
        used_percent = ((total - available) / total) * 100
        status_value = "ok" if used_percent < 90 else "degraded"
        return {
            "memory": status_value,
            "memory_used_percent": round(used_percent, 2),
            "memory_total_bytes": total,
            "memory_available_bytes": available,
        }
    except Exception:
        # Windows/dev hosts without psutil: report unknown (non-fatal).
        return {"memory": "unknown"}


def connector_summary(connector_manager: Any) -> dict[str, int]:
    try:
        records = list(connector_manager.list_records())
    except Exception:
        return {"online": 0, "degraded": 0, "error": 0, "offline": 0, "total": 0}
    online = degraded = error = offline = 0
    for record in records:
        state = getattr(record, "state", None)
        value = getattr(state, "value", state)
        normalized = str(value or "").lower()
        if normalized == ConnectorState.online.value:
            online += 1
        elif normalized == ConnectorState.degraded.value:
            degraded += 1
        elif normalized == ConnectorState.error.value:
            error += 1
        else:
            offline += 1
    return {
        "online": online,
        "degraded": degraded,
        "error": error,
        "offline": offline,
        "total": len(records),
    }


def _uptime_seconds() -> float:
    return round(time.time() - metrics_mod.STARTED_AT, 3)


def build_health_payload(db: Session, connector_manager: Any) -> dict[str, Any]:
    db_checks = check_database(db)
    redis_checks = check_redis()
    disk_checks = check_disk()
    memory_checks = check_memory()
    checks = {**db_checks, **{k: v for k, v in redis_checks.items()}, **{k: v for k, v in disk_checks.items() if k == "disk"}, **{k: v for k, v in memory_checks.items() if k == "memory"}}
    connectors = connector_summary(connector_manager)
    database_ok = db_checks.get("database") == "ok"
    redis_state = redis_checks.get("redis", "not_configured")
    if settings.redis_required:
        redis_ok = redis_state == "ok"
    else:
        redis_ok = redis_state in {"ok", "not_configured"}
    # Top-level status remains dependency-critical (DB / required Redis). Disk and memory are
    # reported as signals without forcing false "degraded" on healthy API hosts.
    status_value = "ok" if database_ok and redis_ok else "degraded"
    if disk_checks.get("disk") == "error" or memory_checks.get("memory") == "error":
        status_value = "degraded"
    return {
        "status": status_value,
        "version": settings.version,
        "api_version": settings.version,
        "build_version": settings.build_version,
        "environment": settings.environment,
        "uptime_seconds": _uptime_seconds(),
        "database": "online" if database_ok else "error",
        "redis": redis_state,
        "disk": disk_checks.get("disk", "unknown"),
        "memory": memory_checks.get("memory", "unknown"),
        "disk_free_percent": disk_checks.get("disk_free_percent"),
        "memory_used_percent": memory_checks.get("memory_used_percent"),
        "simulated": True,
        "connectors": connectors,
        "decision_support": {"advisory_only": True},
        "checks": checks,
    }


def build_ready_payload(db: Session) -> dict[str, Any]:
    checks = check_database(db)
    redis_checks = check_redis()
    checks = {**checks, **redis_checks}
    ready = checks.get("database") == "ok"
    if settings.redis_required and redis_checks.get("redis") not in {"ok"}:
        ready = False
    payload = {
        "ready": ready,
        "status": "ok" if ready else "unavailable",
        "version": settings.version,
        "api_version": settings.version,
        "build_version": settings.build_version,
        "uptime_seconds": _uptime_seconds(),
        "checks": checks,
    }
    if not ready:
        payload["reason"] = "database" if checks.get("database") != "ok" else "redis"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
    return payload


def build_live_payload() -> dict[str, Any]:
    return {
        "live": True,
        "status": "ok",
        "version": settings.version,
        "api_version": settings.version,
        "build_version": settings.build_version,
        "environment": settings.environment,
        "uptime_seconds": _uptime_seconds(),
    }


def build_platform_status(db: Session, connector_manager: Any) -> dict[str, Any]:
    checks = check_database(db)
    redis_checks = check_redis()
    database_state = "online" if checks.get("database") == "ok" else "error"
    return {
        "version": settings.version,
        "api_version": settings.version,
        "build_version": settings.build_version,
        "mode": settings.environment,
        "uptime_seconds": _uptime_seconds(),
        "services": {
            "api": "online",
            "database": database_state,
            "redis": redis_checks.get("redis", "not_configured"),
            "events": "in-process",
            "ai": "decision_engine_advisory",
        },
        "connectors": connector_summary(connector_manager),
        "decision_support": {"advisory_only": True},
        "simulated": True,
    }


def build_ops_health(db: Session, connector_manager: Any) -> dict[str, Any]:
    checks = check_database(db)
    redis_checks = check_redis()
    return {
        "status": "ok" if checks.get("database") == "ok" else "degraded",
        "version": settings.version,
        "database": "online" if checks.get("database") == "ok" else "error",
        "redis": redis_checks.get("redis", "not_configured"),
        "connectors": connector_summary(connector_manager),
        "advisory_only": True,
        "checks": {**checks, **redis_checks},
        "uptime_seconds": _uptime_seconds(),
    }
