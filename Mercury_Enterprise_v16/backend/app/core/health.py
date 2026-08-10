from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.models import ConnectorState
from .config import settings


def check_database(db: Session) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"database": "ok"}
    except Exception:
        return {"database": "error"}


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


def build_health_payload(db: Session, connector_manager: Any) -> dict[str, Any]:
    checks = check_database(db)
    connectors = connector_summary(connector_manager)
    database_ok = checks.get("database") == "ok"
    status_value = "ok" if database_ok else "degraded"
    return {
        "status": status_value,
        "version": settings.version,
        "environment": settings.environment,
        "database": "online" if database_ok else "error",
        "simulated": True,
        "connectors": connectors,
        "decision_support": {"advisory_only": True},
        "checks": checks,
    }


def build_ready_payload(db: Session) -> dict[str, Any]:
    checks = check_database(db)
    ready = checks.get("database") == "ok"
    payload = {
        "ready": ready,
        "version": settings.version,
        "checks": checks,
    }
    if not ready:
        payload["reason"] = "database"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
    return payload


def build_platform_status(db: Session, connector_manager: Any) -> dict[str, Any]:
    checks = check_database(db)
    database_state = "online" if checks.get("database") == "ok" else "error"
    return {
        "version": settings.version,
        "mode": settings.environment,
        "services": {
            "api": "online",
            "database": database_state,
            "events": "in-process",
            "ai": "decision_engine_advisory",
        },
        "connectors": connector_summary(connector_manager),
        "decision_support": {"advisory_only": True},
        "simulated": True,
    }


def build_ops_health(db: Session, connector_manager: Any) -> dict[str, Any]:
    checks = check_database(db)
    return {
        "status": "ok" if checks.get("database") == "ok" else "degraded",
        "version": settings.version,
        "database": "online" if checks.get("database") == "ok" else "error",
        "connectors": connector_summary(connector_manager),
        "advisory_only": True,
        "checks": checks,
    }
