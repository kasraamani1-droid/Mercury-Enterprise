from __future__ import annotations

import asyncio
import logging
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .alerts import AlertManager
from .ai import ThreatRiskEngine
from .assessment import generate_assessment
from .fusion import FusionEngine
from .missions import MissionService, MissionStatus
from .ops import ResponseOrchestrationEngine
from .core.config import settings
from .core.logging import configure_logging
from .audit import list_audit_events, normalize_provenance, record_audit
from .database import SessionLocal, ensure_schema, get_db
from .decision import DecisionEngine
from .models import Evidence, Incident, TimelineEvent
from .schemas import (
    AuditEventOut,
    EvidenceCreate,
    EvidenceOut,
    IncidentCreate,
    IncidentDetail,
    IncidentOut,
    IncidentStatusUpdate,
    SessionContextUpdate,
    SiteOut,
    OrganizationOut,
    TimelineEventCreate,
    TimelineEventOut,
)
from .security.authorization import Role, has_permissions
from .timeline import TimelineManager
from .websocket.manager import manager
from .routers import connectors_router, ops_router
from .connectors.manager import connector_manager
from .connectors.models import ConnectorState

configure_logging()
logger = logging.getLogger("mercury.api")
timeline_manager = TimelineManager()
alert_manager = AlertManager()
threat_engine = ThreatRiskEngine()
fusion_engine = FusionEngine()
mission_service = MissionService()
response_orchestrator = ResponseOrchestrationEngine(
    event_bus_instance=None,
    timeline_manager=None,
    mission_service=mission_service,
    threat_engine=threat_engine,
    fusion_engine=fusion_engine,
)
decision_engine = DecisionEngine(
    event_bus_instance=None,
    timeline_manager=None,
    mission_service=mission_service,
    threat_engine=threat_engine,
    fusion_engine=fusion_engine,
    alert_manager=alert_manager,
    response_orchestrator=response_orchestrator,
)

_sessions: dict[str, dict[str, datetime | str]] = {}
_approvals: dict[str, dict[str, datetime | str | bool | None]] = {}

_organizations: dict[str, OrganizationOut] = {
    "org-aviation-east": OrganizationOut(organization_id="org-aviation-east", name="Mercury Aviation East"),
    "org-aviation-west": OrganizationOut(organization_id="org-aviation-west", name="Mercury Aviation West"),
}
_sites_by_organization: dict[str, list[SiteOut]] = {
    "org-aviation-east": [
        SiteOut(site_id="site-cyul", organization_id="org-aviation-east", name="CYUL Montréal"),
        SiteOut(site_id="site-cyyz", organization_id="org-aviation-east", name="CYYZ Toronto"),
    ],
    "org-aviation-west": [
        SiteOut(site_id="site-cyvr", organization_id="org-aviation-west", name="CYVR Vancouver"),
    ],
}

_ROLE_BY_OPERATOR = {
    "admin": Role.ADMINISTRATOR.value,
    settings.auth_operator: Role.OPERATOR.value,
    "reviewer": Role.REVIEWER.value,
    "viewer": Role.VIEWER.value,
}


class LoginRequest(BaseModel):
    operator: str
    password: str


class ApprovalRequestPayload(BaseModel):
    action: str
    target_id: str | None = None
    reason: str = ""


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _cleanup_expired_sessions(now: datetime | None = None) -> None:
    current = now or utcnow()
    expired = [sid for sid, record in _sessions.items() if record["expires_at"] <= current]
    for sid in expired:
        _sessions.pop(sid, None)


def _create_session(operator: str, role: str) -> tuple[str, datetime]:
    now = utcnow()
    session_id = secrets.token_urlsafe(32)
    expires_at = now + timedelta(seconds=settings.session_ttl_seconds)
    default_organization = next(iter(_organizations.values()))
    default_site = _sites_by_organization[default_organization.organization_id][0]
    _sessions[session_id] = {
        "operator": operator,
        "role": role,
        "organization_id": default_organization.organization_id,
        "site_id": default_site.site_id,
        "created_at": now,
        "expires_at": expires_at,
    }
    return session_id, expires_at


def _validate_session(session_id: str | None) -> dict[str, datetime | str] | None:
    if not session_id:
        return None
    _cleanup_expired_sessions()
    session = _sessions.get(session_id)
    if session is None:
        return None
    if session["expires_at"] <= utcnow():
        _sessions.pop(session_id, None)
        return None
    return session


def _invalidate_session(session_id: str | None) -> None:
    if session_id:
        _sessions.pop(session_id, None)


def _request_session_id(request: Request) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


def _websocket_session_id(websocket: WebSocket) -> str | None:
    return websocket.cookies.get(settings.session_cookie_name)


def require_session(request: Request) -> dict[str, datetime | str]:
    session = _validate_session(_request_session_id(request))
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    request.state.operator = session["operator"]
    request.state.role = session["role"]
    request.state.organization_id = session["organization_id"]
    request.state.site_id = session["site_id"]
    return session


def _get_organization(organization_id: str) -> OrganizationOut:
    organization = _organizations.get(organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


def _get_site_for_organization(organization_id: str, site_id: str) -> SiteOut:
    for site in _sites_by_organization.get(organization_id, []):
        if site.site_id == site_id:
            return site
    raise HTTPException(status_code=404, detail="Site not found")


def _session_context_payload(session: dict[str, datetime | str]) -> dict[str, object]:
    organization_id = str(session["organization_id"])
    site_id = str(session["site_id"])
    organization = _get_organization(organization_id)
    site = _get_site_for_organization(organization_id, site_id)
    return {
        "organization": organization.model_dump(),
        "site": site.model_dump(),
        "organizations": [item.model_dump() for item in _organizations.values()],
        "sites": [item.model_dump() for item in _sites_by_organization.get(organization_id, [])],
    }


def require_permissions(*required: str):
    def dependency(session: dict[str, datetime | str] = Depends(require_session)) -> dict[str, datetime | str]:
        role = str(session.get("role", ""))
        if not has_permissions(role, required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return session

    return dependency


def _create_approval(action: str, target_id: str | None, reason: str, session: dict[str, datetime | str]) -> dict[str, datetime | str | bool | None]:
    approval_id = secrets.token_urlsafe(16)
    record: dict[str, datetime | str | bool | None] = {
        "approval_id": approval_id,
        "action": action,
        "target_id": target_id,
        "reason": reason,
        "status": "pending",
        "requested_by": str(session["operator"]),
        "requested_role": str(session["role"]),
        "organization_id": str(session["organization_id"]),
        "site_id": str(session["site_id"]),
        "created_at": utcnow(),
        "reviewed_by": None,
        "reviewed_at": None,
        "consumed": False,
    }
    _approvals[approval_id] = record
    return record


def _safe_commit_audit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist audit event")


def _approve_request(approval_id: str, reviewer: str) -> dict[str, datetime | str | bool | None]:
    record = _approvals.get(approval_id)
    if record is None:
        raise HTTPException(404, "Approval request not found")
    record["status"] = "approved"
    record["reviewed_by"] = reviewer
    record["reviewed_at"] = utcnow()
    return record


def _require_approved_action(approval_id: str | None, *, action: str, target_id: str) -> None:
    if not approval_id:
        raise HTTPException(status_code=400, detail="Approval required")
    record = _approvals.get(approval_id)
    if record is None:
        raise HTTPException(404, "Approval request not found")
    if bool(record.get("consumed")):
        raise HTTPException(409, "Approval already used")
    if str(record.get("status")) != "approved":
        raise HTTPException(409, "Approval is not approved")
    if str(record.get("action")) != action:
        raise HTTPException(409, "Approval action mismatch")
    if str(record.get("target_id") or "") != target_id:
        raise HTTPException(409, "Approval target mismatch")
    record["consumed"] = True


def seed_demo() -> None:
    if not settings.seed_demo_data:
        return
    db = SessionLocal()
    try:
        if db.scalar(select(Incident).limit(1)):
            return
        incident = Incident(
            title="Drone intrusion detected at Montréal–Trudeau Airport",
            status="open",
            severity="high",
            summary="Simulated demonstration incident for Mercury Enterprise.",
        )
        db.add(incident)
        db.flush()
        t0 = utcnow() - timedelta(minutes=8)
        db.add_all(
            [
                TimelineEvent(incident_id=incident.id, occurred_at=t0, event_type="observation", source="Camera-01", description="Small airborne object detected near the north perimeter.", confidence=62),
                TimelineEvent(incident_id=incident.id, occurred_at=t0 + timedelta(minutes=2), event_type="correlation", source="Mercury Fusion", description="RF and electro-optical observations correlated.", confidence=78),
                TimelineEvent(incident_id=incident.id, occurred_at=t0 + timedelta(minutes=5), event_type="operator_note", source="Operator A", description="Target remained inside the protected operating area.", confidence=90),
            ]
        )
        db.add_all(
            [
                Evidence(
                    incident_id=incident.id,
                    evidence_type="image",
                    source="Camera-01",
                    title="North perimeter frame",
                    content="Simulated evidence reference: frame-001.jpg",
                    confidence=62,
                    provenance="simulated",
                    created_by="seed",
                    organization_id="org-aviation-east",
                    site_id="site-cyul",
                ),
                Evidence(
                    incident_id=incident.id,
                    evidence_type="operator_note",
                    source="Operator A",
                    title="Visual review",
                    content="Object appears consistent with a small civilian UAV; identity unconfirmed.",
                    confidence=74,
                    provenance="simulated",
                    created_by="seed",
                    organization_id="org-aviation-east",
                    site_id="site-cyul",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


async def heartbeat() -> None:
    while True:
        await asyncio.sleep(5)
        await manager.broadcast({"type": "heartbeat", "timestamp": utcnow().isoformat(), "version": settings.version})


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()
    seed_demo()
    timeline_manager.add_event(
        event_type="mission.started",
        severity="info",
        source="startup",
        message="Mission timeline initialized",
        metadata={"environment": settings.environment},
    )
    alert_manager.create_alert(
        incident_id=None,
        severity="info",
        title="System started",
        message="Backend services initialized",
        source="startup",
        metadata={"environment": settings.environment},
    )
    startup_assessment = threat_engine.evaluate(78, 82)
    logger.info(
        "Startup AI assessment score=%s confidence=%s level=%s",
        startup_assessment["score"],
        startup_assessment["confidence"],
        startup_assessment["level"],
    )
    fusion_engine.clear()
    app.state.mission_service = mission_service
    app.state.response_orchestrator = response_orchestrator
    app.state.decision_engine = decision_engine
    await connector_manager.start_all()
    task = asyncio.create_task(heartbeat())
    logger.info("Mercury %s started in %s mode", settings.version, settings.environment)
    try:
        yield
    finally:
        task.cancel()
        await connector_manager.stop_all()
        logger.info("Mercury shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Production-oriented reference platform. Operational feeds remain simulated unless configured otherwise.",
    lifespan=lifespan,
)
app.include_router(connectors_router)
app.include_router(ops_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled request error request_id=%s", request_id)
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
    response.headers["x-request-id"] = request_id
    response.headers["x-response-time-ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
    return response


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "version": settings.version, "environment": settings.environment, "database": "online", "simulated": True}


@app.get("/api/v1/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"ready": True, "version": settings.version}


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    role = _ROLE_BY_OPERATOR.get(payload.operator)
    if role is None or payload.password != settings.auth_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    session_id, expires_at = _create_session(payload.operator, role)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    try:
        session = _sessions[session_id]
        record_audit(
            db,
            action="auth.login",
            actor=payload.operator,
            actor_role=role,
            organization_id=str(session["organization_id"]),
            site_id=str(session["site_id"]),
            target_type="session",
            target_id=session_id,
            source="api",
            outcome="success",
            origin="operator",
            details="",
        )
        _safe_commit_audit(db)
    except Exception:
        logger.exception("Failed to record auth.login audit")
    return {"authenticated": True, "operator": payload.operator, "role": role, "expires_at": expires_at.isoformat()}


@app.post("/api/v1/auth/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    session = _validate_session(_request_session_id(request))
    if session is not None:
        try:
            record_audit(
                db,
                action="auth.logout",
                actor=str(session["operator"]),
                actor_role=str(session["role"]),
                organization_id=str(session["organization_id"]),
                site_id=str(session["site_id"]),
                target_type="session",
                target_id=_request_session_id(request),
                source="api",
                outcome="success",
                origin="operator",
                details="",
            )
            _safe_commit_audit(db)
        except Exception:
            logger.exception("Failed to record auth.logout audit")
    _invalidate_session(_request_session_id(request))
    response.delete_cookie(key=settings.session_cookie_name, path="/", secure=settings.session_cookie_secure, samesite=settings.session_cookie_samesite)
    return {"authenticated": False}


@app.get("/api/v1/auth/session")
def session_status(request: Request):
    session = _validate_session(_request_session_id(request))
    if session is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "operator": str(session["operator"]),
        "role": str(session["role"]),
        "organization_id": str(session["organization_id"]),
        "site_id": str(session["site_id"]),
        "expires_at": session["expires_at"].isoformat(),
    }


@app.get("/api/v1/auth/context")
def get_session_context(session: dict[str, datetime | str] = Depends(require_session)):
    return {
        "operator": str(session["operator"]),
        "role": str(session["role"]),
        **_session_context_payload(session),
    }


@app.post("/api/v1/auth/context")
def update_session_context(
    payload: SessionContextUpdate,
    session: dict[str, datetime | str] = Depends(require_session),
    db: Session = Depends(get_db),
):
    old_organization_id = str(session["organization_id"])
    old_site_id = str(session["site_id"])
    current_organization_id = old_organization_id
    next_organization_id = payload.organization_id or current_organization_id
    _get_organization(next_organization_id)

    available_sites = _sites_by_organization.get(next_organization_id, [])
    if not available_sites:
        raise HTTPException(status_code=409, detail="Organization has no configured sites")

    if payload.site_id:
        _get_site_for_organization(next_organization_id, payload.site_id)
        next_site_id = payload.site_id
    elif payload.organization_id and payload.organization_id != current_organization_id:
        next_site_id = available_sites[0].site_id
    else:
        current_site_id = str(session["site_id"])
        try:
            _get_site_for_organization(next_organization_id, current_site_id)
            next_site_id = current_site_id
        except HTTPException:
            next_site_id = available_sites[0].site_id

    session["organization_id"] = next_organization_id
    session["site_id"] = next_site_id

    try:
        record_audit(
            db,
            action="auth.context",
            actor=str(session["operator"]),
            actor_role=str(session["role"]),
            organization_id=str(next_organization_id),
            site_id=str(next_site_id),
            target_type="session",
            target_id=None,
            source="api",
            outcome="success",
            origin="operator",
            details=f"{old_organization_id}/{old_site_id}->{next_organization_id}/{next_site_id}",
        )
        _safe_commit_audit(db)
    except Exception:
        logger.exception("Failed to record auth.context audit")

    return {
        "operator": str(session["operator"]),
        "role": str(session["role"]),
        **_session_context_payload(session),
    }


@app.post("/api/v1/approvals", dependencies=[Depends(require_permissions("approval.request"))])
def create_approval_request(
    payload: ApprovalRequestPayload,
    session: dict[str, datetime | str] = Depends(require_session),
    db: Session = Depends(get_db),
):
    record = _create_approval(payload.action, payload.target_id, payload.reason, session)
    record_audit(
        db,
        action="approval.request",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="approval",
        target_id=str(record["approval_id"]),
        source="api",
        outcome="success",
        origin="operator",
        details=payload.reason or payload.action,
    )
    db.commit()
    return {
        "approval_id": str(record["approval_id"]),
        "status": str(record["status"]),
        "action": str(record["action"]),
        "target_id": record["target_id"],
        "requested_by": str(record["requested_by"]),
        "requested_role": str(record["requested_role"]),
        "created_at": record["created_at"].isoformat(),
    }


@app.get("/api/v1/approvals", dependencies=[Depends(require_permissions("approval.review"))])
def list_approvals(status_filter: str | None = None):
    records = list(_approvals.values())
    if status_filter:
        records = [item for item in records if str(item.get("status")) == status_filter]
    return [
        {
            "approval_id": str(item["approval_id"]),
            "status": str(item["status"]),
            "action": str(item["action"]),
            "target_id": item["target_id"],
            "requested_by": str(item["requested_by"]),
            "requested_role": str(item["requested_role"]),
            "reviewed_by": item["reviewed_by"],
            "consumed": bool(item["consumed"]),
        }
        for item in records
    ]


@app.post("/api/v1/approvals/{approval_id}/approve", dependencies=[Depends(require_permissions("approval.review"))])
def approve_request(
    approval_id: str,
    session: dict[str, datetime | str] = Depends(require_session),
    db: Session = Depends(get_db),
):
    record = _approve_request(approval_id, str(session["operator"]))
    organization_id = str(record.get("organization_id") or session["organization_id"])
    site_id = str(record.get("site_id") or session["site_id"])
    record_audit(
        db,
        action="approval.approve",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=organization_id,
        site_id=site_id,
        target_type="approval",
        target_id=approval_id,
        source="api",
        outcome="success",
        origin="operator",
        details="",
    )
    db.commit()
    return {
        "approval_id": str(record["approval_id"]),
        "status": str(record["status"]),
        "reviewed_by": str(record["reviewed_by"]),
        "reviewed_at": record["reviewed_at"].isoformat(),
    }


@app.get("/api/v1/incidents", response_model=list[IncidentOut])
def list_incidents(db: Session = Depends(get_db)):
    return db.scalars(select(Incident).order_by(Incident.created_at.desc())).all()


@app.post("/api/v1/incidents", response_model=IncidentOut, status_code=201)
async def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("incident.create")),
):
    incident = Incident(**payload.model_dump())
    db.add(incident)
    db.flush()
    record_audit(
        db,
        action="incident.create",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="incident",
        target_id=incident.id,
        source="api",
        outcome="success",
        origin="operator",
        details=payload.title,
    )
    db.commit()
    db.refresh(incident)
    await manager.broadcast({"type": "incident.created", "incident_id": incident.id, "severity": incident.severity})
    return incident


@app.get("/api/v1/incidents/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    incident.events.sort(key=lambda item: item.occurred_at)
    return incident


@app.patch("/api/v1/incidents/{incident_id}/status", response_model=IncidentOut, dependencies=[Depends(require_permissions("incident.update"))])
async def update_incident_status(
    incident_id: str,
    payload: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_session),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    status_value = str(payload.status).lower()
    consumed_approval = False
    if status_value in {"resolved", "closed"} and str(session.get("role")) != Role.ADMINISTRATOR.value:
        _require_approved_action(payload.approval_id, action="incident.resolve", target_id=incident_id)
        consumed_approval = True
    incident.status = payload.status
    if consumed_approval:
        approval_record = _approvals.get(str(payload.approval_id or ""))
        record_audit(
            db,
            action="approval.consume",
            actor=str(session["operator"]),
            actor_role=str(session["role"]),
            organization_id=str(
                (approval_record or {}).get("organization_id") or session["organization_id"]
            ),
            site_id=str((approval_record or {}).get("site_id") or session["site_id"]),
            target_type="approval",
            target_id=str(payload.approval_id),
            source="api",
            outcome="success",
            origin="operator",
            details=f"incident.resolve:{incident_id}",
        )
    record_audit(
        db,
        action="incident.status",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="incident",
        target_id=incident_id,
        source="api",
        outcome="success",
        origin="operator",
        details=f"status={payload.status}",
    )
    db.commit()
    db.refresh(incident)
    await manager.broadcast({"type": "incident.status", "incident_id": incident.id, "status": incident.status})
    return incident


@app.post("/api/v1/incidents/{incident_id}/events", response_model=TimelineEventOut, status_code=201)
async def add_event(
    incident_id: str,
    payload: TimelineEventCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("incident.event")),
):
    if not db.get(Incident, incident_id):
        raise HTTPException(404, "Incident not found")
    event = TimelineEvent(incident_id=incident_id, **payload.model_dump())
    db.add(event)
    db.flush()
    record_audit(
        db,
        action="incident.event",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="incident",
        target_id=incident_id,
        source="api",
        outcome="success",
        origin="operator",
        details=payload.event_type,
    )
    db.commit()
    db.refresh(event)
    await manager.broadcast({"type": "timeline.event", "incident_id": incident_id, "event_type": event.event_type})
    return event


@app.post("/api/v1/incidents/{incident_id}/evidence", response_model=EvidenceOut, status_code=201)
def add_evidence(
    incident_id: str,
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("incident.evidence")),
):
    if not db.get(Incident, incident_id):
        raise HTTPException(404, "Incident not found")
    provenance = normalize_provenance(payload.provenance, default="operator_entered")
    evidence = Evidence(
        incident_id=incident_id,
        evidence_type=payload.evidence_type,
        source=payload.source,
        title=payload.title,
        content=payload.content,
        confidence=payload.confidence,
        provenance=provenance,
        created_by=str(session["operator"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )
    db.add(evidence)
    db.flush()
    record_audit(
        db,
        action="incident.evidence",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="evidence",
        target_id=evidence.id,
        source="api",
        outcome="success",
        origin="operator",
        details=provenance,
    )
    db.commit()
    db.refresh(evidence)
    return evidence


@app.get("/api/v1/incidents/{incident_id}/assessment")
def get_assessment(incident_id: str, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return generate_assessment(incident)


@app.get("/api/v1/incidents/{incident_id}/report")
def incident_report(incident_id: str, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return {
        "schema_version": "1.0",
        "incident": {"id": incident.id, "title": incident.title, "status": incident.status, "severity": incident.severity, "summary": incident.summary},
        "timeline": [{"time": event.occurred_at.isoformat(), "type": event.event_type, "source": event.source, "description": event.description, "confidence": event.confidence} for event in sorted(incident.events, key=lambda item: item.occurred_at)],
        "evidence": [
            {
                "type": item.evidence_type,
                "source": item.source,
                "title": item.title,
                "content": item.content,
                "confidence": item.confidence,
                "provenance": item.provenance,
                "created_by": item.created_by,
                "organization_id": item.organization_id,
                "site_id": item.site_id,
            }
            for item in incident.evidence
        ],
        "generated_at": utcnow().isoformat(),
        "simulated": True,
    }


@app.get("/api/v1/audit", response_model=list[AuditEventOut])
def list_audit(
    action: str | None = None,
    target_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("audit.read")),
):
    return list_audit_events(
        db,
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        action=action,
        target_id=target_id,
        limit=limit,
        retention_days=settings.audit_retention_days,
    )


@app.get("/api/v1/platform/status")
def platform_status():
    return {"version": settings.version, "mode": settings.environment, "services": {"api": "online", "database": "online", "events": "online", "ai": "rule-engine"}, "simulated": True}


@app.get("/api/v1/alerts")
def list_alerts(incident_id: str | None = None, limit: int = 50):
    return [alert.to_dict() for alert in alert_manager.get_alerts(incident_id=incident_id, limit=limit)]


@app.post("/api/v1/alerts/{alert_id}/ack")
def acknowledge_alert(alert_id: str, _: dict[str, datetime | str] = Depends(require_permissions("alerts.ack"))):
    alert = alert_manager.acknowledge(alert_id)
    if alert is None:
        raise HTTPException(404, "Alert not found")
    return alert.to_dict()


@app.get("/api/v1/integrations")
def integrations():
    return {"version": settings.version, "configured": 12, "online": 9, "sandbox": 3, "simulated": True}


@app.get("/api/v1/compliance")
def compliance():
    return {"version": settings.version, "control_coverage": 92, "open_findings": 4, "certified": False, "simulated": True}


@app.get("/api/v1/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    platform_services = {"api": "online", "database": "online", "events": "online", "ai": "rule-engine"}
    connected_services = sum(1 for status in platform_services.values() if status == "online")

    alerts = alert_manager.get_alerts(limit=250)
    active_alerts = [alert for alert in alerts if not alert.acknowledged]
    critical_alerts = [alert for alert in active_alerts if str(alert.severity).lower() == "critical"]
    acknowledged_alerts = [alert for alert in alerts if alert.acknowledged]

    missions = mission_service.list_missions(status=MissionStatus.ACTIVE)
    incidents = db.scalars(select(Incident)).all()

    timeline_events = timeline_manager.get_events(sort_desc=True)
    decision_events = [entry for entry in timeline_events if str(entry.event_type).startswith("decision.")]
    decision_timeline = [
        {
            "timestamp": entry.timestamp.isoformat(),
            "decision": entry.message,
            "operator_acknowledged": False,
        }
        for entry in decision_events[:5]
    ]

    connector_records = connector_manager.list_records()
    connectors_by_category = {record.category: record for record in connector_records}

    def connector_state(category: str) -> str:
        record = connectors_by_category.get(category)
        if record is None:
            return ConnectorState.offline.value
        return record.state.value

    sensor_online = sum(1 for record in connector_records if record.state == ConnectorState.online)
    sensor_warning = sum(1 for record in connector_records if record.state == ConnectorState.degraded)
    sensor_offline = sum(1 for record in connector_records if record.state in {ConnectorState.offline, ConnectorState.error})

    mission_status = "active" if missions else "idle"
    alert_status = "critical" if critical_alerts else "active" if active_alerts else "stable"
    selected_recommendation = None
    decision_status = "review_required" if decision_events else "clear"
    connector_states = {
        "ads_b": connector_state("aviation"),
        "rf": ConnectorState.offline.value,
        "cameras": ConnectorState.offline.value,
        "weather": connector_state("weather"),
        "ml_engine": ConnectorState.offline.value,
    }
    connector_values = list(connector_states.values())
    connector_status = "degraded" if ConnectorState.degraded.value in connector_values else "offline" if all(value == ConnectorState.offline.value for value in connector_values) else "online"

    return {
        "platform": {
            "version": settings.version,
            "mode": settings.environment,
            "status": "online",
            "connected_services": connected_services,
            "services": platform_services,
            "simulated": True,
        },
        "timeline": {"events": len(timeline_events)},
        "services": {"active_tracks": 0},
        "alerts": {"total": len(alerts), "active": len(active_alerts), "status": alert_status},
        "missions": {"active": len(missions), "status": mission_status},
        "decisions": {
            "pending_human_review": len(decision_events),
            "highest_threat_level": "unknown",
            "selected_recommendation": selected_recommendation,
            "status": decision_status,
        },
        "fleet_health": {
            "aircraft_online": 0,
            "active_sensors": sensor_online,
            "incidents": len(incidents),
            "ai_confidence": 0,
        },
        "connector_health": connector_states | {"status": connector_status},
        "ai_confidence_trends": {"samples": []},
        "decision_timeline": decision_timeline,
        "active_alerts_summary": {
            "active": len(active_alerts),
            "critical": len(critical_alerts),
            "acknowledged": len(acknowledged_alerts),
        },
        "sensor_health": {
            "online": sensor_online,
            "warning": sensor_warning,
            "offline": sensor_offline,
        },
    }


@app.websocket("/api/v1/ws")
async def websocket_gateway(websocket: WebSocket):
    session = _validate_session(_websocket_session_id(websocket))
    if session is None:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket)
    try:
        context = _session_context_payload(session)
        await websocket.send_json(
            {
                "type": "connected",
                "version": settings.version,
                "simulated": True,
                "operator": session["operator"],
                "role": session["role"],
                "organization": context["organization"],
                "site": context["site"],
            }
        )
        while True:
            message = await websocket.receive_text()
            if message.lower() == "ping":
                await websocket.send_json({"type": "pong", "timestamp": utcnow().isoformat()})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
