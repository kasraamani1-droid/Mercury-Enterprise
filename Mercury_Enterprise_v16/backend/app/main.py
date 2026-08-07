from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from .database import Base, SessionLocal, engine, get_db
from .decision import DecisionEngine
from .models import Evidence, Incident, TimelineEvent
from .schemas import (
    EvidenceCreate,
    EvidenceOut,
    IncidentCreate,
    IncidentDetail,
    IncidentOut,
    IncidentStatusUpdate,
    TimelineEventCreate,
    TimelineEventOut,
)
from .security.api_key import require_api_key
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


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
                Evidence(incident_id=incident.id, evidence_type="image", source="Camera-01", title="North perimeter frame", content="Simulated evidence reference: frame-001.jpg", confidence=62),
                Evidence(incident_id=incident.id, evidence_type="operator_note", source="Operator A", title="Visual review", content="Object appears consistent with a small civilian UAV; identity unconfirmed.", confidence=74),
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
    Base.metadata.create_all(bind=engine)
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


@app.get("/api/v1/incidents", response_model=list[IncidentOut])
def list_incidents(db: Session = Depends(get_db)):
    return db.scalars(select(Incident).order_by(Incident.created_at.desc())).all()


@app.post("/api/v1/incidents", response_model=IncidentOut, status_code=201, dependencies=[Depends(require_api_key)])
async def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    incident = Incident(**payload.model_dump())
    db.add(incident)
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


@app.patch("/api/v1/incidents/{incident_id}/status", response_model=IncidentOut, dependencies=[Depends(require_api_key)])
async def update_incident_status(incident_id: str, payload: IncidentStatusUpdate, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    incident.status = payload.status
    db.commit()
    db.refresh(incident)
    await manager.broadcast({"type": "incident.status", "incident_id": incident.id, "status": incident.status})
    return incident


@app.post("/api/v1/incidents/{incident_id}/events", response_model=TimelineEventOut, status_code=201, dependencies=[Depends(require_api_key)])
async def add_event(incident_id: str, payload: TimelineEventCreate, db: Session = Depends(get_db)):
    if not db.get(Incident, incident_id):
        raise HTTPException(404, "Incident not found")
    event = TimelineEvent(incident_id=incident_id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    await manager.broadcast({"type": "timeline.event", "incident_id": incident_id, "event_type": event.event_type})
    return event


@app.post("/api/v1/incidents/{incident_id}/evidence", response_model=EvidenceOut, status_code=201, dependencies=[Depends(require_api_key)])
def add_evidence(incident_id: str, payload: EvidenceCreate, db: Session = Depends(get_db)):
    if not db.get(Incident, incident_id):
        raise HTTPException(404, "Incident not found")
    evidence = Evidence(incident_id=incident_id, **payload.model_dump())
    db.add(evidence)
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
        "evidence": [{"type": item.evidence_type, "source": item.source, "title": item.title, "content": item.content, "confidence": item.confidence} for item in incident.evidence],
        "generated_at": utcnow().isoformat(),
        "simulated": True,
    }


@app.get("/api/v1/platform/status")
def platform_status():
    return {"version": settings.version, "mode": settings.environment, "services": {"api": "online", "database": "online", "events": "online", "ai": "rule-engine"}, "simulated": True}


@app.get("/api/v1/alerts")
def list_alerts(incident_id: str | None = None, limit: int = 50):
    return [alert.to_dict() for alert in alert_manager.get_alerts(incident_id=incident_id, limit=limit)]


@app.post("/api/v1/alerts/{alert_id}/ack")
def acknowledge_alert(alert_id: str):
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
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "version": settings.version, "simulated": True})
        while True:
            message = await websocket.receive_text()
            if message.lower() == "ping":
                await websocket.send_json({"type": "pong", "timestamp": utcnow().isoformat()})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
