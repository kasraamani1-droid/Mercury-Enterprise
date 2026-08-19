from __future__ import annotations

import asyncio
import logging
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .alerts import AlertManager
from .ai import ThreatRiskEngine
from .assessment import generate_assessment
from .fusion import FusionEngine
from .missions import MissionService, MissionStatus
from .ops import ResponseOrchestrationEngine
from .core.config import settings
from .core.health import build_health_payload, build_live_payload, build_platform_status, build_ready_payload
from .core.logging import bind_request_context, configure_logging
from .core import metrics as metrics_mod
from .security.api_key import api_key_configured, extract_api_key, resolve_api_key_session
from .security.sessions import session_store
from .audit import (
    ACTION_API_ACCESS,
    ACTION_LOGIN,
    ACTION_LOGIN_FAILURE,
    ACTION_LOGOUT,
    ACTION_SECURITY_EVENT,
    list_audit_events,
    normalize_provenance,
    record_audit,
)
from .database import SessionLocal, ensure_schema, get_db
from .decision import DecisionEngine
from .models import ApprovalRequest, Evidence, Incident, TimelineEvent
from .reporting import build_report_history, build_report_summary
from .schemas import (
    AuditEventOut,
    DecisionEvaluateRequest,
    DecisionReviewRequest,
    EvidenceCreate,
    EvidenceOut,
    IncidentCreate,
    IncidentDetail,
    IncidentOut,
    IncidentStatusUpdate,
    SessionContextUpdate,
    TimelineEventCreate,
    TimelineEventOut,
)
from .security.authorization import Role
from .security.runtime_authz import require_allowed
from .security.operators import authenticate_credentials, hash_password, operator_store
from .security.rate_limit import classify_rate_limit_path, client_key, rate_limiter
from .security.oidc import oidc_service, public_auth_config
from .security.csrf import csrf_blocked
from .shared import clamp_page
from .timeline import TimelineManager
from .openapi_docs import OPENAPI_TAGS, enrich_openapi
from .routers import admin_router, connectors_router, ops_router
from .org.router import router as org_router
from .org.service import OrganizationService
from .fleet.router import router as fleet_router
from .fleet.service import FleetService
from .components.router import router as components_router
from .components.service import ComponentService
from .publications.router import library_router, router as publications_router
from .publications.service import PublicationService
from .personnel.router import router as personnel_router
from .personnel.service import PersonnelService
from .maintenance.router import router as maintenance_router
from .maintenance.service import MaintenanceService
from .work_orders.router import router as work_orders_router
from .work_orders.service import WorkOrderService
from .planning.router import router as planning_router
from .planning.service import PlanningService
from .logistics.router import router as logistics_router
from .logistics.service import LogisticsService
from .platform.router import router as platform_router
from .platform.service import PlatformService
from .marketplace.router import router as marketplace_router
from .marketplace.service import MarketplaceService
from .oem.router import router as oem_router
from .oem.service import OemService
from .authority.router import router as authority_router
from .authority.service import AuthorityService
from .fabric.router import router as fabric_router
from .fabric.service import FabricService
from .ecosystem.router import router as ecosystem_router
from .ecosystem.service import EcosystemService
from .connect.router import router as connect_router
from .connect.service import ConnectService
from .network.router import router as network_router
from .network.service import NetworkService
from .twin.router import router as twin_router
from .twin.service import TwinService
from .plugins.router import router as plugins_router
from .plugins.service import PluginService
from .event_fabric.router import router as event_fabric_router
from .event_fabric.service import EventFabricService
from .connectors.manager import connector_manager
from .connectors.models import ConnectorState
from .websocket.manager import manager

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
    connector_manager=connector_manager,
)

# Back-compat alias for admin metrics; prefer session_store.
_sessions = session_store


def directory_roles() -> dict[str, str]:
    """Production omits shared demo reviewer/viewer unless MERCURY_SEED_DEMO=true."""
    roles: dict[str, str] = {"admin": Role.ADMINISTRATOR.value}
    operator_name = (settings.auth_operator or "operator").strip() or "operator"
    roles[operator_name] = Role.OPERATOR.value
    if settings.seed_demo_data:
        roles.setdefault("operator", Role.OPERATOR.value)
        roles["reviewer"] = Role.REVIEWER.value
        roles["viewer"] = Role.VIEWER.value
    return roles


# Bootstrap mutable operator directory from static roles + shared password.
operator_store.bootstrap(
    auth_operator=settings.auth_operator,
    auth_password=settings.auth_password,
    role_by_operator=directory_roles(),
)


class LoginRequest(BaseModel):
    operator: str = Field(min_length=1, max_length=120, description="Directory username")
    password: str = Field(min_length=1, max_length=200, description="Operator password")

    model_config = {
        "json_schema_extra": {
            "examples": [{"operator": "operator", "password": "your-password"}],
        }
    }


class ApprovalRequestPayload(BaseModel):
    action: str = Field(description="Approval action, e.g. incident.resolve")
    target_id: str | None = Field(default=None, description="Target resource id (incident id for resolve)")
    reason: str = Field(default="", description="Operator reason recorded on the request")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _cleanup_expired_sessions(now: datetime | None = None) -> None:
    session_store.cleanup_expired(now)


def _record_login_rate_limit_audit() -> None:
    """Identity.md: exhausted login bucket writes security.login_failure (rate_limited)."""
    try:
        db = SessionLocal()
        try:
            record_audit(
                db,
                action=ACTION_LOGIN_FAILURE,
                actor="unknown",
                actor_role="",
                organization_id="org-aviation-east",
                site_id="site-cyul",
                target_type="auth",
                target_id="login",
                source="api",
                outcome="failure",
                origin="system",
                details="rate_limited",
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to record rate-limited login audit")


def seed_organizations() -> None:
    """Idempotent company/org/site/membership seed for multi-tenant RBAC."""
    db = SessionLocal()
    try:
        OrganizationService(db).ensure_seed_data(
            default_password_hash=hash_password(settings.auth_password),
            operator_roles=directory_roles(),
            auth_password=settings.auth_password,
        )
        operator_store.hydrate_from_db(db)
    finally:
        db.close()


def seed_fleet() -> None:
    """Idempotent aircraft registry catalog + east-org demo fleet."""
    db = SessionLocal()
    try:
        FleetService(db).ensure_seed_data()
    finally:
        db.close()


def seed_components() -> None:
    """Idempotent ATA/catalog + east-org serialized component demo."""
    db = SessionLocal()
    try:
        ComponentService(db).ensure_seed_data()
    finally:
        db.close()


def seed_publications() -> None:
    """Idempotent publication types + east-org technical library demos (locators only)."""
    db = SessionLocal()
    try:
        PublicationService(db).ensure_seed_data()
    finally:
        db.close()


def seed_personnel() -> None:
    """Idempotent personnel / qualification demo for org-aviation-east."""
    db = SessionLocal()
    try:
        PersonnelService(db).ensure_seed_data()
    finally:
        db.close()


def seed_maintenance() -> None:
    """Idempotent critical policies, fault codes, and demo maintenance task."""
    db = SessionLocal()
    try:
        MaintenanceService(db).ensure_seed_data()
    finally:
        db.close()


def seed_work_orders() -> None:
    """Idempotent work package / work order / job card demo."""
    db = SessionLocal()
    try:
        WorkOrderService(db).ensure_seed_data()
    finally:
        db.close()


def seed_planning() -> None:
    """Idempotent maintenance planning / MPD / AD / forecast demo."""
    db = SessionLocal()
    try:
        PlanningService(db).ensure_seed_data()
    finally:
        db.close()


def seed_logistics() -> None:
    """Idempotent Program B logistics demo (warehouse, stock, tools, vendors)."""
    db = SessionLocal()
    try:
        LogisticsService(db).seed_demo("org-aviation-east")
    finally:
        db.close()


def seed_platform() -> None:
    """Idempotent Program A platform foundation (templates, flags, workflow, facilities)."""
    db = SessionLocal()
    try:
        PlatformService(db).seed_platform("org-aviation-east")
    finally:
        db.close()


def seed_aeos_domains() -> None:
    """Idempotent marketplace / OEM / authority readiness registries."""
    db = SessionLocal()
    try:
        MarketplaceService(db).seed("org-aviation-east")
        OemService(db).seed()
        AuthorityService(db).seed()
    finally:
        db.close()


def seed_fabric() -> None:
    """Idempotent Program 11 Universal Data Fabric (passports, catalog, policies)."""
    db = SessionLocal()
    try:
        FabricService(db).seed_fabric("org-aviation-east")
    finally:
        db.close()


def seed_ecosystem() -> None:
    """Idempotent Program 12 Aviation Digital Ecosystem + Mercury Connect."""
    db = SessionLocal()
    try:
        EcosystemService(db).seed("org-aviation-east")
        ConnectService(db).seed("org-aviation-east")
    finally:
        db.close()


def seed_network() -> None:
    """Idempotent Program 14 Mercury Aviation Network."""
    db = SessionLocal()
    try:
        NetworkService(db).seed("org-aviation-east")
    finally:
        db.close()


def seed_twin() -> None:
    """Idempotent Program 15 Mercury Digital Twin."""
    db = SessionLocal()
    try:
        TwinService(db).seed("org-aviation-east")
    finally:
        db.close()


def seed_plugins() -> None:
    """Idempotent Program 16 Mercury Plugin Platform."""
    db = SessionLocal()
    try:
        PluginService(db).seed("org-aviation-east")
    finally:
        db.close()


def seed_event_fabric() -> None:
    """Idempotent Program 17 Mercury Enterprise Event Fabric."""
    db = SessionLocal()
    try:
        EventFabricService(db).seed("org-aviation-east")
    finally:
        db.close()


def _create_session(operator: str, role: str, *, auth_method: str = "session") -> tuple[str, datetime]:
    now = utcnow()
    session_id = secrets.token_urlsafe(32)
    expires_at = now + timedelta(seconds=settings.session_ttl_seconds)
    db = SessionLocal()
    try:
        svc = OrganizationService(db)
        organization_id, site_id = svc.default_context_for_user(operator, role)
        effective_role = svc.effective_role_for_org(operator, role, organization_id)
    finally:
        db.close()
    record = {
        "operator": operator,
        "role": effective_role,
        "organization_id": organization_id,
        "site_id": site_id,
        "created_at": now,
        "expires_at": expires_at,
        "auth_method": auth_method,
    }
    session_store.save(session_id, record)
    return session_id, expires_at


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _validate_session(session_id: str | None) -> dict[str, datetime | str] | None:
    return session_store.get(session_id)


def _invalidate_session(session_id: str | None) -> None:
    session_store.delete(session_id)


def _request_session_id(request: Request) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


def _websocket_session_id(websocket: WebSocket) -> str | None:
    return websocket.cookies.get(settings.session_cookie_name)


def require_session(request: Request) -> dict[str, datetime | str]:
    session_id = _request_session_id(request)
    session = _validate_session(session_id)
    if session is None:
        session = resolve_api_key_session(request)
        if session is None:
            if api_key_configured() and extract_api_key(request):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        request.state.session_id = None
        request.state.auth_method = "api_key"
    else:
        request.state.session_id = session_id
        request.state.auth_method = "session"
    request.state.operator = session["operator"]
    request.state.role = session["role"]
    request.state.organization_id = session["organization_id"]
    request.state.site_id = session["site_id"]
    return session


def _session_context_payload(session: dict[str, datetime | str], db: Session | None = None) -> dict[str, object]:
    organization_id = str(session["organization_id"])
    site_id = str(session["site_id"])
    operator = str(session["operator"])
    # Access checks use login-directory role, not possibly membership-adjusted session role.
    global_role = operator_store.get(operator)
    access_role = global_role["role"] if global_role else str(session["role"])
    owns_db = db is None
    if owns_db:
        db = SessionLocal()
    assert db is not None
    try:
        svc = OrganizationService(db)
        organization = svc.get_organization_out(organization_id)
        site = svc.get_site_out(organization_id, site_id)
        organizations = svc.organizations_for_session(operator, access_role)
        sites = svc.sites_for_session(operator, access_role, organization_id)
        return {
            "organization": organization.model_dump(),
            "site": site.model_dump(),
            "organizations": [item.model_dump() for item in organizations],
            "sites": [item.model_dump() for item in sites],
        }
    finally:
        if owns_db:
            db.close()


def require_permissions(*required: str):
    def dependency(
        session: dict[str, datetime | str] = Depends(require_session),
        db: Session = Depends(get_db),
    ) -> dict[str, datetime | str]:
        require_allowed(db, session, required, detail="Insufficient permissions")
        return session

    return dependency


def _session_site_filter(session: dict[str, datetime | str]):
    return (
        Incident.organization_id == str(session["organization_id"]),
        Incident.site_id == str(session["site_id"]),
    )


def _get_scoped_incident(db: Session, incident_id: str, session: dict[str, datetime | str]) -> Incident:
    incident = db.get(Incident, incident_id)
    if (
        incident is None
        or str(incident.organization_id or "") != str(session["organization_id"])
        or str(incident.site_id or "") != str(session["site_id"])
    ):
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


async def _broadcast_tenant_event(
    payload: dict[str, object],
    *,
    organization_id: str,
    site_id: str,
) -> None:
    """Fan-out incident/timeline events only to sockets stamped with this tenant."""
    await manager.broadcast(
        {**payload, "organization_id": organization_id, "site_id": site_id},
        organization_id=organization_id,
        site_id=site_id,
    )


def _approval_site_filter(session: dict[str, datetime | str]):
    return (
        ApprovalRequest.organization_id == str(session["organization_id"]),
        ApprovalRequest.site_id == str(session["site_id"]),
    )


def _get_scoped_approval(
    db: Session,
    approval_id: str,
    session: dict[str, datetime | str],
    *,
    for_update: bool = False,
) -> ApprovalRequest:
    if for_update:
        row = db.scalar(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id).with_for_update()
        )
    else:
        row = db.get(ApprovalRequest, approval_id)
    if (
        row is None
        or str(row.organization_id or "") != str(session["organization_id"])
        or str(row.site_id or "") != str(session["site_id"])
    ):
        raise HTTPException(status_code=404, detail="Approval request not found")
    return row


def _create_approval(
    db: Session,
    action: str,
    target_id: str | None,
    reason: str,
    session: dict[str, datetime | str],
) -> ApprovalRequest:
    row = ApprovalRequest(
        id=secrets.token_urlsafe(16),
        action=action,
        target_id=target_id,
        reason=reason or "",
        status="pending",
        requested_by=str(session["operator"]),
        requested_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        created_at=utcnow(),
        reviewed_by=None,
        reviewed_at=None,
        consumed=False,
    )
    db.add(row)
    db.flush()
    return row


def _safe_commit_audit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist audit event")


def _approve_request(
    db: Session,
    approval_id: str,
    reviewer: str,
    session: dict[str, datetime | str],
) -> ApprovalRequest:
    row = _get_scoped_approval(db, approval_id, session, for_update=True)
    if str(row.status) != "pending":
        raise HTTPException(status_code=409, detail="Approval is not pending")
    row.status = "approved"
    row.reviewed_by = reviewer
    row.reviewed_at = utcnow()
    return row


def _require_approved_action(
    db: Session,
    approval_id: str | None,
    *,
    action: str,
    target_id: str,
    session: dict[str, datetime | str],
) -> ApprovalRequest:
    if not approval_id:
        raise HTTPException(status_code=400, detail="Approval required")
    row = _get_scoped_approval(db, approval_id, session, for_update=True)
    if bool(row.consumed):
        raise HTTPException(409, "Approval already used")
    if str(row.status) != "approved":
        raise HTTPException(409, "Approval is not approved")
    if str(row.action) != action:
        raise HTTPException(409, "Approval action mismatch")
    if str(row.target_id or "") != target_id:
        raise HTTPException(409, "Approval target mismatch")
    row.consumed = True
    return row


def seed_demo() -> None:
    if not settings.seed_demo_data:
        return
    db = SessionLocal()
    try:
        # Task 17: stamp legacy unscoped incidents so site reports remain usable in demos.
        legacy = list(db.scalars(select(Incident).where(Incident.site_id.is_(None))).all())
        for item in legacy:
            item.organization_id = item.organization_id or "org-aviation-east"
            item.site_id = "site-cyul"
        if legacy:
            db.commit()

        existing_seed_evidence = db.scalar(select(Evidence).where(Evidence.created_by == "seed").limit(1))
        existing_incident = db.scalar(select(Incident).limit(1))
        if existing_incident and existing_seed_evidence:
            return

        if existing_incident is None:
            incident = Incident(
                title="Drone intrusion detected at Montréal–Trudeau Airport",
                status="open",
                severity="high",
                summary="Simulated demonstration incident for Mercury Enterprise.",
                organization_id="org-aviation-east",
                site_id="site-cyul",
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
        else:
            incident = existing_incident

        if existing_seed_evidence is None:
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
                        organization_id=incident.organization_id or "org-aviation-east",
                        site_id=incident.site_id or "site-cyul",
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
                        organization_id=incident.organization_id or "org-aviation-east",
                        site_id=incident.site_id or "site-cyul",
                    ),
                ]
            )
        db.commit()
    finally:
        db.close()


async def heartbeat() -> None:
    while True:
        await asyncio.sleep(5)
        _cleanup_expired_sessions()
        await manager.broadcast({"type": "heartbeat", "timestamp": utcnow().isoformat(), "version": settings.version})


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_startup()
    ensure_schema()
    seed_organizations()
    seed_fleet()
    seed_components()
    seed_publications()
    seed_personnel()
    seed_maintenance()
    seed_work_orders()
    seed_planning()
    seed_logistics()
    seed_platform()
    seed_aeos_domains()
    seed_fabric()
    seed_ecosystem()
    seed_network()
    seed_twin()
    seed_plugins()
    seed_event_fabric()
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
    description=(
        "Mercury AEOS REST API. Operator authentication uses an opaque HttpOnly session cookie "
        "(not JWT access/refresh tokens). Optional machine auth: X-API-Key / Authorization Bearer "
        "when MERCURY_API_KEY is configured. Interactive documentation: /docs (Swagger UI) and /redoc."
    ),
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)
app.include_router(connectors_router)
app.include_router(ops_router)
app.include_router(admin_router)
app.include_router(org_router)
app.include_router(fleet_router)
app.include_router(components_router)
app.include_router(publications_router)
app.include_router(library_router)
app.include_router(personnel_router)
app.include_router(maintenance_router)
app.include_router(work_orders_router)
app.include_router(planning_router)
app.include_router(logistics_router)
app.include_router(platform_router)
app.include_router(marketplace_router)
app.include_router(oem_router)
app.include_router(authority_router)
app.include_router(fabric_router)
app.include_router(ecosystem_router)
app.include_router(connect_router)
app.include_router(network_router)
app.include_router(twin_router)
app.include_router(plugins_router)
app.include_router(event_fabric_router)


def custom_openapi():
    """Generated OpenAPI plus RC1 documentation enrichment (tags, auth, errors)."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    app.openapi_schema = enrich_openapi(schema, app)
    return app.openapi_schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
if settings.https_enabled and (settings.domain or "").strip():
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[settings.domain, f"www.{settings.domain}", "localhost", "127.0.0.1"],
    )
    app.add_middleware(
        ProxyHeadersMiddleware,
        trusted_hosts=[settings.domain, f"www.{settings.domain}"],
    )


@app.middleware("http")
async def csrf_origin_guard(request: Request, call_next):
    if csrf_blocked(request, cors_origins=settings.cors_origins, domain=settings.domain):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "CSRF origin rejected"})
    return await call_next(request)


@app.middleware("http")
async def rate_limit_requests(request: Request, call_next):
    bucket = classify_rate_limit_path(request.url.path)
    if bucket is not None:
        limit = (
            settings.rate_limit_login_per_minute
            if bucket == "login"
            else settings.rate_limit_api_per_minute
        )
        key = f"{bucket}:{client_key(request.client.host if request.client else None, request.headers.get('x-forwarded-for'))}"
        if not rate_limiter.allow(key, limit=limit, window_seconds=60.0):
            metrics_mod.observe_rate_limit_block(bucket)
            if bucket == "login":
                _record_login_rate_limit_audit()
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded", "retry_after_seconds": 60},
                headers={"Retry-After": "60"},
            )
    return await call_next(request)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    correlation_id = request.headers.get("x-correlation-id") or request_id
    session = _validate_session(_request_session_id(request))
    user_id = str(session["operator"]) if session else ""
    bind_request_context(request_id=request_id, correlation_id=correlation_id, user_id=user_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error path=%s", request.url.path)
        metrics_mod.observe_request(
            method=request.method,
            path=request.url.path,
            status_code=500,
            duration_seconds=time.perf_counter() - started,
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
    elapsed = time.perf_counter() - started
    elapsed_ms = elapsed * 1000
    response.headers["x-request-id"] = request_id
    response.headers["x-correlation-id"] = correlation_id
    response.headers["x-response-time-ms"] = f"{elapsed_ms:.1f}"
    if settings.metrics_enabled:
        metrics_mod.observe_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=elapsed,
        )
        metrics_mod.set_active_users(session_store.count())
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.1f",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    # API access audit for mutating authenticated calls (and all /admin writes already audited).
    if (
        settings.audit_api_access
        and session is not None
        and request.method.upper() in {"POST", "PATCH", "PUT", "DELETE"}
        and not request.url.path.startswith("/admin/")
        and request.url.path.startswith("/api/")
        and request.url.path not in {"/api/v1/auth/login", "/api/v1/auth/logout"}
    ):
        try:
            db = SessionLocal()
            try:
                record_audit(
                    db,
                    action=ACTION_API_ACCESS,
                    actor=str(session["operator"]),
                    actor_role=str(session["role"]),
                    organization_id=str(session["organization_id"]),
                    site_id=str(session["site_id"]),
                    target_type="endpoint",
                    target_id=f"{request.method.upper()} {request.url.path}",
                    source="api",
                    outcome="success" if response.status_code < 400 else "failure",
                    origin="operator",
                    details=f"status={response.status_code}",
                )
                db.commit()
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to record api.access audit")
    return response


@app.get("/health")
def root_health(db: Session = Depends(get_db)):
    return build_health_payload(db, connector_manager)


@app.get("/ready")
def root_ready(db: Session = Depends(get_db)):
    return build_ready_payload(db)


@app.get("/live")
def root_live():
    return build_live_payload()


@app.get("/metrics")
def prometheus_metrics():
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    payload, content_type = metrics_mod.render_prometheus()
    return Response(content=payload, media_type=content_type)


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)):
    return build_health_payload(db, connector_manager)


@app.get("/api/v1/ready")
def ready(db: Session = Depends(get_db)):
    return build_ready_payload(db)


@app.get("/api/v1/platform/status")
def platform_status(
    db: Session = Depends(get_db),
    _: dict[str, datetime | str] = Depends(require_permissions("platform.read")),
):
    return build_platform_status(db, connector_manager)


@app.post(
    "/api/v1/auth/login",
    tags=["auth"],
    summary="Operator login",
    description=(
        "Verifies credentials against the OrgUser directory (Argon2id; legacy SHA-256 is upgraded on success). "
        "Creates a server-side session and sets an HttpOnly cookie. Does not return a JWT or refresh token."
    ),
)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    if not settings.password_login_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password authentication is disabled. Sign in with SSO.",
        )
    role = authenticate_credentials(db, payload.operator, payload.password)
    if role is None:
        metrics_mod.observe_login(success=False)
        try:
            seed_organizations()
            org_db = SessionLocal()
            try:
                svc = OrganizationService(org_db)
                orgs = svc.repo.list_organizations()
                if orgs:
                    sites = svc.repo.list_sites(organization_id=orgs[0].id)
                    default_organization_id = orgs[0].id
                    default_site_id = sites[0].id if sites else ""
                else:
                    default_organization_id = "org-aviation-east"
                    default_site_id = "site-cyul"
            finally:
                org_db.close()
            record_audit(
                db,
                action=ACTION_LOGIN_FAILURE,
                actor=payload.operator[:120],
                actor_role="",
                organization_id=default_organization_id,
                site_id=default_site_id,
                target_type="session",
                target_id=payload.operator[:120],
                source="api",
                outcome="failure",
                origin="operator",
                details="invalid_credentials",
            )
            record_audit(
                db,
                action=ACTION_SECURITY_EVENT,
                actor=payload.operator[:120],
                actor_role="",
                organization_id=default_organization_id,
                site_id=default_site_id,
                target_type="auth",
                target_id="login",
                source="api",
                outcome="failure",
                origin="system",
                details="invalid_credentials",
            )
            _safe_commit_audit(db)
        except Exception:
            logger.exception("Failed to record login failure audit")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    metrics_mod.observe_login(success=True)
    _invalidate_session(_request_session_id(request))
    session_id, expires_at = _create_session(payload.operator, role, auth_method="password")
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=500, detail="Session could not be established")
    effective_role = str(session["role"])
    _set_session_cookie(response, session_id)
    try:
        record_audit(
            db,
            action=ACTION_LOGIN,
            actor=payload.operator,
            actor_role=effective_role,
            organization_id=str(session["organization_id"]),
            site_id=str(session["site_id"]),
            target_type="session",
            target_id="session",
            source="api",
            outcome="success",
            origin="operator",
            details="method=password",
        )
        _safe_commit_audit(db)
    except Exception:
        logger.exception("Failed to record auth.login audit")
    metrics_mod.set_active_users(session_store.count())
    return {
        "authenticated": True,
        "operator": payload.operator,
        "role": effective_role,
        "expires_at": expires_at.isoformat(),
        "auth_method": "password",
    }

@app.post(
    "/api/v1/auth/logout",
    tags=["auth"],
    summary="Operator logout",
    description="Invalidates the server-side session and clears the session cookie. Idempotent when no session is present.",
)
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    session = _validate_session(_request_session_id(request))
    if session is not None:
        try:
            record_audit(
                db,
                action=ACTION_LOGOUT,
                actor=str(session["operator"]),
                actor_role=str(session["role"]),
                organization_id=str(session["organization_id"]),
                site_id=str(session["site_id"]),
                target_type="session",
                target_id="session",
                source="api",
                outcome="success",
                origin="operator",
                details="",
            )
            _safe_commit_audit(db)
        except Exception:
            logger.exception("Failed to record auth.logout audit")
    _invalidate_session(_request_session_id(request))
    metrics_mod.set_active_users(session_store.count())
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )
    return {"authenticated": False}


@app.get(
    "/api/v1/auth/session",
    tags=["auth"],
    summary="Session probe",
    description="Returns authenticated=false without a valid cookie (HTTP 200). Does not require a session.",
)
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
        "auth_method": str(session.get("auth_method") or "session"),
    }


@app.get(
    "/api/v1/auth/public-config",
    tags=["auth"],
    summary="Public authentication and deployment flags",
    description="Unauthenticated. No secrets. Used by the login overlay and SIM workspace visibility.",
)
def auth_public_config():
    return public_auth_config()


@app.get(
    "/api/v1/auth/oidc/login",
    tags=["auth"],
    summary="Start OIDC authorization-code login",
    description="Redirects to the configured IdP. Fails closed when OIDC is not configured.",
)
def oidc_login():
    url = oidc_service.start_authorization()
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@app.get(
    "/api/v1/auth/oidc/callback",
    tags=["auth"],
    summary="OIDC authorization-code callback",
    description="Exchanges the authorization code, maps the IdP subject onto a provisioned OrgUser, and sets the session cookie.",
)
def oidc_callback(
    request: Request,
    db: Session = Depends(get_db),
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
):
    if error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC authentication was denied")
    claims = oidc_service.complete(code=code, state=state)
    user = oidc_service.resolve_directory_user(db, claims)
    role = (user.platform_role or Role.VIEWER.value).strip() or Role.VIEWER.value
    operator_store.register_role(user.username, role)
    _invalidate_session(_request_session_id(request))
    session_id, expires_at = _create_session(user.username, role, auth_method="oidc")
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=500, detail="Session could not be established")
    try:
        record_audit(
            db,
            action=ACTION_LOGIN,
            actor=user.username,
            actor_role=str(session["role"]),
            organization_id=str(session["organization_id"]),
            site_id=str(session["site_id"]),
            target_type="session",
            target_id="session",
            source="api",
            outcome="success",
            origin="operator",
            details="method=oidc",
        )
        _safe_commit_audit(db)
    except Exception:
        logger.exception("Failed to record OIDC auth.login audit")
    metrics_mod.observe_login(success=True)
    metrics_mod.set_active_users(session_store.count())
    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept and "text/html" not in accept:
        payload = JSONResponse(
            {
                "authenticated": True,
                "operator": user.username,
                "role": str(session["role"]),
                "expires_at": expires_at.isoformat(),
                "auth_method": "oidc",
            }
        )
        _set_session_cookie(payload, session_id)
        return payload
    redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    _set_session_cookie(redirect, session_id)
    return redirect


@app.get(
    "/api/v1/auth/context",
    tags=["auth"],
    summary="Get tenant session context",
    description="Requires a valid session cookie. Returns operator, role, active organization/site, and switchable tenants.",
)
def get_session_context(
    session: dict[str, datetime | str] = Depends(require_session),
    db: Session = Depends(get_db),
):
    return {
        "operator": str(session["operator"]),
        "role": str(session["role"]),
        **_session_context_payload(session, db),
    }


@app.post(
    "/api/v1/auth/context",
    tags=["auth"],
    summary="Switch tenant session context",
    description="Updates the active organization/site on the server-side session. API-key principals cannot switch context.",
)
def update_session_context(
    payload: SessionContextUpdate,
    request: Request,
    session: dict[str, datetime | str] = Depends(require_session),
    db: Session = Depends(get_db),
):
    if getattr(request.state, "auth_method", "session") == "api_key":
        raise HTTPException(status_code=400, detail="API key sessions cannot switch organization context")
    old_organization_id = str(session["organization_id"])
    old_site_id = str(session["site_id"])
    current_organization_id = old_organization_id
    next_organization_id = payload.organization_id or current_organization_id
    svc = OrganizationService(db)
    operator = str(session["operator"])
    # Platform admins keep global admin; others must hold membership for target org.
    global_role = operator_store.get(operator)
    fallback_role = global_role["role"] if global_role else str(session["role"])
    try:
        svc.assert_org_access(username=operator, session_role=fallback_role, organization_id=next_organization_id)
    except HTTPException as exc:
        if exc.status_code == 403:
            try:
                record_audit(
                    db,
                    action=ACTION_SECURITY_EVENT,
                    actor=operator,
                    actor_role=fallback_role,
                    organization_id=old_organization_id,
                    site_id=old_site_id,
                    target_type="organization",
                    target_id=next_organization_id,
                    source="api",
                    outcome="failure",
                    origin="operator",
                    details="organization_access_denied",
                )
                _safe_commit_audit(db)
            except Exception:
                logger.exception("Failed to record denied auth.context audit")
        raise
    svc.get_organization_out(next_organization_id)

    available_sites = svc.sites_for_session(operator, fallback_role, next_organization_id)
    if not available_sites:
        raise HTTPException(status_code=409, detail="Organization has no configured sites")

    if payload.site_id:
        svc.get_site_out(next_organization_id, payload.site_id)
        next_site_id = payload.site_id
    elif payload.organization_id and payload.organization_id != current_organization_id:
        next_site_id = available_sites[0].site_id
    else:
        current_site_id = str(session["site_id"])
        try:
            svc.get_site_out(next_organization_id, current_site_id)
            next_site_id = current_site_id
        except HTTPException:
            next_site_id = available_sites[0].site_id

    session["organization_id"] = next_organization_id
    session["site_id"] = next_site_id
    session["role"] = svc.effective_role_for_org(operator, fallback_role, next_organization_id)
    session_id = getattr(request.state, "session_id", None) or _request_session_id(request)
    if session_id:
        session_store.save(str(session_id), session)

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
        **_session_context_payload(session, db),
    }


@app.post("/api/v1/approvals", dependencies=[Depends(require_permissions("approval.request"))])
def create_approval_request(
    payload: ApprovalRequestPayload,
    session: dict[str, datetime | str] = Depends(require_session),
    db: Session = Depends(get_db),
):
    record = _create_approval(db, payload.action, payload.target_id, payload.reason, session)
    record_audit(
        db,
        action="approval.request",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="approval",
        target_id=str(record.id),
        source="api",
        outcome="success",
        origin="operator",
        details=payload.reason or payload.action,
    )
    db.commit()
    db.refresh(record)
    return {
        "approval_id": str(record.id),
        "status": str(record.status),
        "action": str(record.action),
        "target_id": record.target_id,
        "requested_by": str(record.requested_by),
        "requested_role": str(record.requested_role),
        "organization_id": str(record.organization_id),
        "site_id": str(record.site_id),
        "created_at": record.created_at.isoformat(),
    }


@app.get("/api/v1/approvals", dependencies=[Depends(require_permissions("approval.review"))])
def list_approvals(
    status_filter: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: dict[str, datetime | str] = Depends(require_session),
    db: Session = Depends(get_db),
):
    stmt = (
        select(ApprovalRequest)
        .where(*_approval_site_filter(session))
        .order_by(ApprovalRequest.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(ApprovalRequest.status == status_filter)
    lim, off = clamp_page(limit, offset)
    records = list(db.scalars(stmt.offset(off).limit(lim)).all())
    return [
        {
            "approval_id": str(item.id),
            "status": str(item.status),
            "action": str(item.action),
            "target_id": item.target_id,
            "requested_by": str(item.requested_by),
            "requested_role": str(item.requested_role),
            "organization_id": str(item.organization_id),
            "site_id": str(item.site_id),
            "reviewed_by": item.reviewed_by,
            "consumed": bool(item.consumed),
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        }
        for item in records
    ]


@app.post("/api/v1/approvals/{approval_id}/approve", dependencies=[Depends(require_permissions("approval.review"))])
def approve_request(
    approval_id: str,
    session: dict[str, datetime | str] = Depends(require_session),
    db: Session = Depends(get_db),
):
    record = _approve_request(db, approval_id, str(session["operator"]), session)
    record_audit(
        db,
        action="approval.approve",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(record.organization_id),
        site_id=str(record.site_id),
        target_type="approval",
        target_id=approval_id,
        source="api",
        outcome="success",
        origin="operator",
        details="",
    )
    db.commit()
    db.refresh(record)
    return {
        "approval_id": str(record.id),
        "status": str(record.status),
        "reviewed_by": str(record.reviewed_by),
        "reviewed_at": record.reviewed_at.isoformat() if record.reviewed_at else None,
        "organization_id": str(record.organization_id),
        "site_id": str(record.site_id),
    }


@app.get("/api/v1/incidents", response_model=list[IncidentOut])
def list_incidents(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("incident.read")),
):
    capped, start = clamp_page(limit, offset)
    stmt = (
        select(Incident)
        .where(*_session_site_filter(session))
        .order_by(Incident.created_at.desc())
        .offset(start)
        .limit(capped)
    )
    return db.scalars(stmt).all()


@app.post("/api/v1/incidents", response_model=IncidentOut, status_code=201)
async def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("incident.create")),
):
    incident = Incident(
        **payload.model_dump(),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )
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
    await _broadcast_tenant_event(
        {"type": "incident.created", "incident_id": incident.id, "severity": incident.severity},
        organization_id=str(incident.organization_id),
        site_id=str(incident.site_id),
    )
    return incident


@app.get("/api/v1/incidents/{incident_id}", response_model=IncidentDetail)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("incident.read")),
):
    incident = _get_scoped_incident(db, incident_id, session)
    incident.events.sort(key=lambda item: item.occurred_at)
    return incident


@app.patch("/api/v1/incidents/{incident_id}/status", response_model=IncidentOut, dependencies=[Depends(require_permissions("incident.update"))])
async def update_incident_status(
    incident_id: str,
    payload: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_session),
):
    incident = _get_scoped_incident(db, incident_id, session)
    status_value = str(payload.status).lower()
    consumed_approval = False
    approval_record: ApprovalRequest | None = None
    if status_value in {"resolved", "closed"} and str(session.get("role")) != Role.ADMINISTRATOR.value:
        approval_record = _require_approved_action(
            db,
            payload.approval_id,
            action="incident.resolve",
            target_id=incident_id,
            session=session,
        )
        consumed_approval = True
    incident.status = payload.status
    if consumed_approval and approval_record is not None:
        record_audit(
            db,
            action="approval.consume",
            actor=str(session["operator"]),
            actor_role=str(session["role"]),
            organization_id=str(approval_record.organization_id),
            site_id=str(approval_record.site_id),
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
        organization_id=str(incident.organization_id),
        site_id=str(incident.site_id),
        target_type="incident",
        target_id=incident_id,
        source="api",
        outcome="success",
        origin="operator",
        details=f"status={payload.status}",
    )
    db.commit()
    db.refresh(incident)
    await _broadcast_tenant_event(
        {"type": "incident.status", "incident_id": incident.id, "status": incident.status},
        organization_id=str(incident.organization_id),
        site_id=str(incident.site_id),
    )
    return incident


@app.post("/api/v1/incidents/{incident_id}/events", response_model=TimelineEventOut, status_code=201)
async def add_event(
    incident_id: str,
    payload: TimelineEventCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("incident.event")),
):
    incident = _get_scoped_incident(db, incident_id, session)
    event = TimelineEvent(incident_id=incident.id, **payload.model_dump())
    db.add(event)
    db.flush()
    record_audit(
        db,
        action="incident.event",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(incident.organization_id),
        site_id=str(incident.site_id),
        target_type="incident",
        target_id=incident.id,
        source="api",
        outcome="success",
        origin="operator",
        details=payload.event_type,
    )
    db.commit()
    db.refresh(event)
    await _broadcast_tenant_event(
        {"type": "timeline.event", "incident_id": incident.id, "event_type": event.event_type},
        organization_id=str(incident.organization_id),
        site_id=str(incident.site_id),
    )
    return event


@app.post("/api/v1/incidents/{incident_id}/evidence", response_model=EvidenceOut, status_code=201)
def add_evidence(
    incident_id: str,
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("incident.evidence")),
):
    incident = _get_scoped_incident(db, incident_id, session)
    provenance = normalize_provenance(payload.provenance, default="operator_entered")
    evidence = Evidence(
        incident_id=incident.id,
        evidence_type=payload.evidence_type,
        source=payload.source,
        title=payload.title,
        content=payload.content,
        confidence=payload.confidence,
        provenance=provenance,
        created_by=str(session["operator"]),
        organization_id=str(incident.organization_id),
        site_id=str(incident.site_id),
    )
    db.add(evidence)
    db.flush()
    record_audit(
        db,
        action="incident.evidence",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(incident.organization_id),
        site_id=str(incident.site_id),
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
def get_assessment(
    incident_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("incident.read")),
):
    incident = _get_scoped_incident(db, incident_id, session)
    return generate_assessment(incident)


@app.get("/api/v1/incidents/{incident_id}/report")
def incident_report(
    incident_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("incident.read")),
):
    incident = _get_scoped_incident(db, incident_id, session)
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


@app.get("/api/v1/reports/summary")
def report_summary(
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("reports.read")),
):
    return build_report_summary(
        db,
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        start=start,
        end=end,
    )


@app.get("/api/v1/reports/history")
def report_history(
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("reports.read")),
):
    return build_report_history(
        db,
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        start=start,
        end=end,
        limit=limit,
    )


@app.get("/api/v1/alerts")
def list_alerts(
    incident_id: str | None = None,
    limit: int = 50,
    session: dict[str, datetime | str] = Depends(require_permissions("alerts.read")),
):
    return [
        alert.to_dict()
        for alert in alert_manager.get_alerts(
            incident_id=incident_id,
            limit=limit,
            organization_id=str(session["organization_id"]),
            site_id=str(session["site_id"]),
        )
    ]


@app.post("/api/v1/alerts/{alert_id}/ack")
def acknowledge_alert(
    alert_id: str,
    session: dict[str, datetime | str] = Depends(require_permissions("alerts.ack")),
):
    alert = alert_manager.acknowledge(
        alert_id,
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )
    if alert is None:
        raise HTTPException(404, "Alert not found")
    return alert.to_dict()


@app.get("/api/v1/integrations")
def integrations(_: dict[str, datetime | str] = Depends(require_permissions("platform.read"))):
    return {"version": settings.version, "configured": 12, "online": 9, "sandbox": 3, "simulated": True}


@app.get("/api/v1/compliance")
def compliance(_: dict[str, datetime | str] = Depends(require_permissions("platform.read"))):
    return {"version": settings.version, "control_coverage": 92, "open_findings": 4, "certified": False, "simulated": True}


@app.post("/api/v1/decisions/evaluate", dependencies=[Depends(require_permissions("decisions.read"))])
def evaluate_decision(
    payload: DecisionEvaluateRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_session),
):
    if payload.threat_score is None and not payload.threat_level:
        raise HTTPException(status_code=422, detail="threat_score or threat_level is required")
    active_alerts: list | bool | None = payload.active_alerts
    if isinstance(active_alerts, bool):
        active_alerts = [{"title": "operator_flagged_alert"}] if active_alerts else []
    context = {
        "mission_id": payload.mission_id,
        "track_id": payload.track_id,
        "threat_level": payload.threat_level,
        "threat_score": payload.threat_score,
        "active_alerts": active_alerts or [],
        "operator_constraints": payload.operator_constraints or [],
        "response_recommendations": payload.response_recommendations or [],
        "organization_id": str(session["organization_id"]),
        "site_id": str(session["site_id"]),
    }
    try:
        result = decision_engine.evaluate(context)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record_audit(
        db,
        action="decision.evaluate",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="decision",
        target_id=str(result.get("decision_id") or ""),
        source="api",
        outcome="success",
        origin="operator",
        details=f"Advisory evaluation for mission {payload.mission_id}",
    )
    db.commit()
    return result


@app.get("/api/v1/decisions", dependencies=[Depends(require_permissions("decisions.read"))])
def list_decisions(
    limit: int = 20,
    session: dict[str, datetime | str] = Depends(require_session),
):
    return decision_engine.list_decisions(
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        limit=limit,
    )


@app.get("/api/v1/decisions/{decision_id}", dependencies=[Depends(require_permissions("decisions.read"))])
def get_decision(
    decision_id: str,
    session: dict[str, datetime | str] = Depends(require_session),
):
    result = decision_engine.get_decision(
        decision_id,
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return result


@app.post("/api/v1/decisions/{decision_id}/review", dependencies=[Depends(require_permissions("decisions.review"))])
def review_decision(
    decision_id: str,
    payload: DecisionReviewRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_session),
):
    try:
        result = decision_engine.apply_review(
            decision_id=decision_id,
            state=payload.state,
            comment=payload.comment,
            actor=str(session["operator"]),
            organization_id=str(session["organization_id"]),
            site_id=str(session["site_id"]),
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Decision not found") from None
    except ValueError as exc:
        detail = str(exc)
        if detail == "comment_required":
            raise HTTPException(status_code=422, detail="comment is required when state=commented") from exc
        raise HTTPException(status_code=409, detail="Invalid review transition") from exc
    record_audit(
        db,
        action="decision.review",
        actor=str(session["operator"]),
        actor_role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
        target_type="decision",
        target_id=decision_id,
        source="api",
        outcome="success",
        origin="operator",
        details=f"Review state={payload.state}",
    )
    db.commit()
    return result


@app.get("/api/v1/dashboard/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_permissions("dashboard.read")),
):
    platform_services = {"api": "online", "database": "online", "events": "online", "ai": "decision_engine_advisory"}
    connected_services = sum(1 for status in platform_services.values() if status == "online")

    org_id = str(session["organization_id"])
    site_id = str(session["site_id"])
    alerts = alert_manager.get_alerts(limit=250, organization_id=org_id, site_id=site_id)
    active_alerts = [alert for alert in alerts if not alert.acknowledged]
    critical_alerts = [alert for alert in active_alerts if str(alert.severity).lower() == "critical"]
    acknowledged_alerts = [alert for alert in alerts if alert.acknowledged]

    missions = mission_service.list_missions(status=MissionStatus.ACTIVE)
    incident_count = db.scalar(
        select(func.count()).select_from(Incident).where(
            Incident.organization_id == org_id,
            Incident.site_id == site_id,
        )
    ) or 0
    fleet_operational = FleetService(db).repo.count_operational_aircraft(organization_id=org_id)

    stored_decisions = decision_engine.list_decisions(organization_id=org_id, site_id=site_id, limit=20)
    pending_reviews = sum(1 for item in stored_decisions if str((item.get("review") or {}).get("state") or "") == "pending")
    latest = stored_decisions[0] if stored_decisions else None
    selected_recommendation = (latest or {}).get("selected_recommendation")
    latest_threat = str(((latest or {}).get("metadata") or {}).get("threat_level") or "unknown")
    warning_count = len((latest or {}).get("warnings") or []) if latest else 0
    alternative_count = len((latest or {}).get("ranked_actions") or []) if latest else 0
    latest_review_state = ((latest or {}).get("review") or {}).get("state") if latest else None
    decision_status = "review_required" if pending_reviews else "clear"

    decision_timeline = []
    for item in stored_decisions[:5]:
        review_state = str((item.get("review") or {}).get("state") or "pending")
        selected_name = ((item.get("selected_recommendation") or {}) or {}).get("name")
        decision_timeline.append(
            {
                "timestamp": item.get("created_at"),
                "decision": item.get("reasoning") or item.get("context_summary") or "Decision update",
                "operator_acknowledged": review_state in {"acknowledged", "commented"},
                "decision_id": item.get("decision_id"),
                "review_state": review_state,
                "selected_name": selected_name,
                "warning_count": len(item.get("warnings") or []),
            }
        )

    if not decision_timeline:
        timeline_events = timeline_manager.get_events(sort_desc=True)
        decision_events = [entry for entry in timeline_events if str(entry.event_type).startswith("decision.")]
        decision_timeline = [
            {
                "timestamp": entry.timestamp.isoformat(),
                "decision": entry.message,
                "operator_acknowledged": False,
                "decision_id": None,
                "review_state": None,
                "selected_name": None,
                "warning_count": 0,
            }
            for entry in decision_events[:5]
        ]
        if decision_events and pending_reviews == 0 and latest is None:
            pending_reviews = len(decision_events)
            decision_status = "review_required"

    timeline_events = timeline_manager.get_events(sort_desc=True)

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
            "pending_human_review": pending_reviews,
            "highest_threat_level": latest_threat,
            "selected_recommendation": selected_recommendation,
            "status": decision_status,
            "warning_count": warning_count,
            "alternative_count": alternative_count,
            "latest_decision_id": (latest or {}).get("decision_id"),
            "latest_review_state": latest_review_state,
            "advisory_only": True,
        },
        "fleet_health": {
            "aircraft_online": int(fleet_operational),
            "active_sensors": sensor_online,
            "incidents": int(incident_count),
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
    # Tenant stamp required by ConnectionManager (RB-02); approvals work is orthogonal.
    await manager.connect(
        websocket,
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )
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
