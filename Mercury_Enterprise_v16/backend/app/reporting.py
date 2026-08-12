from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .connectors.manager import connector_manager
from .connectors.models import ConnectorState
from .models import AuditEvent, Evidence, Incident


def _parse_window(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    window_end = end or datetime.utcnow()
    window_start = start or (window_end - timedelta(days=7))
    if window_start > window_end:
        window_start, window_end = window_end, window_start
    return window_start, window_end


def build_report_summary(
    db: Session,
    *,
    organization_id: str,
    site_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict:
    window_start, window_end = _parse_window(start, end)

    incidents = list(
        db.scalars(
            select(Incident)
            .where(Incident.organization_id == organization_id)
            .where(Incident.site_id == site_id)
            .where(Incident.created_at >= window_start)
            .where(Incident.created_at <= window_end)
        ).all()
    )
    open_count = sum(1 for item in incidents if str(item.status).lower() in {"open", "active", "investigating"})
    resolved_count = sum(1 for item in incidents if str(item.status).lower() in {"resolved", "closed"})
    total = len(incidents)
    resolution_rate = round((resolved_count / total) * 100, 1) if total else 0.0

    response_seconds: list[float] = []
    for incident in incidents:
        delta = (incident.updated_at - incident.created_at).total_seconds()
        if delta >= 0:
            response_seconds.append(delta)
    median_response = int(median(response_seconds)) if response_seconds else None

    audit_events = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .where(AuditEvent.site_id == site_id)
            .where(AuditEvent.occurred_at >= window_start)
            .where(AuditEvent.occurred_at <= window_end)
        ).all()
    )

    evidence_items = list(
        db.scalars(
            select(Evidence)
            .where(Evidence.organization_id == organization_id)
            .where(Evidence.site_id == site_id)
            .where(Evidence.created_at >= window_start)
            .where(Evidence.created_at <= window_end)
        ).all()
    )
    provenance = {
        "simulated_evidence": sum(1 for item in evidence_items if item.provenance == "simulated"),
        "operator_entered_evidence": sum(1 for item in evidence_items if item.provenance == "operator_entered"),
        "system_generated_evidence": sum(1 for item in evidence_items if item.provenance == "system_generated"),
    }

    by_hour = {f"{hour:02d}": 0 for hour in range(24)}
    for incident in incidents:
        by_hour[f"{incident.created_at.hour:02d}"] += 1
    trends = {"incidents_by_hour": [{"hour": hour, "count": count} for hour, count in by_hour.items()]}

    connector_records = connector_manager.list_records()
    connector_online = sum(1 for item in connector_records if item.state == ConnectorState.online)
    connector_degraded = sum(1 for item in connector_records if item.state == ConnectorState.degraded)
    connector_error = sum(1 for item in connector_records if item.state == ConnectorState.error)

    return {
        "organization_id": organization_id,
        "site_id": site_id,
        "window": {"start": window_start.isoformat(), "end": window_end.isoformat()},
        "kpis": {
            "incidents_total": total,
            "incidents_open": open_count,
            "incidents_resolved": resolved_count,
            "resolution_rate": resolution_rate,
            "median_response_seconds": median_response,
            "audit_events": len(audit_events),
            "evidence_items": len(evidence_items),
            "connector_online": connector_online,
            "connector_degraded": connector_degraded,
            "connector_error": connector_error,
        },
        "trends": trends,
        "provenance": provenance,
        "disclaimer": (
            "Historical summary derived from Mercury operational data. "
            "Advisory only; no automated action."
        ),
    }


def build_report_history(
    db: Session,
    *,
    organization_id: str,
    site_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 200,
) -> list[dict]:
    window_start, window_end = _parse_window(start, end)
    clamped = max(1, min(int(limit), 500))
    incidents = list(
        db.scalars(
            select(Incident)
            .options(selectinload(Incident.evidence))
            .where(Incident.organization_id == organization_id)
            .where(Incident.site_id == site_id)
            .where(Incident.created_at >= window_start)
            .where(Incident.created_at <= window_end)
            .order_by(Incident.created_at.desc())
            .limit(clamped)
        ).all()
    )

    create_audits = {
        str(item.target_id): item
        for item in db.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .where(AuditEvent.site_id == site_id)
            .where(AuditEvent.action == "incident.create")
        ).all()
        if item.target_id
    }

    rows: list[dict] = []
    for incident in incidents:
        audit = create_audits.get(incident.id)
        provenance_values = sorted({item.provenance for item in incident.evidence if item.provenance})
        response_seconds = max(0, int((incident.updated_at - incident.created_at).total_seconds()))
        rows.append(
            {
                "id": incident.id,
                "site_id": incident.site_id or site_id,
                "organization_id": incident.organization_id or organization_id,
                "title": incident.title,
                "type": incident.title,
                "severity": incident.severity,
                "status": incident.status,
                "detected_at": incident.created_at.isoformat(),
                "response_seconds": response_seconds,
                "operator": audit.actor if audit else "",
                "provenance": ",".join(provenance_values),
            }
        )
    return rows
