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

from .assessment import generate_assessment
from .core.config import settings
from .core.logging import configure_logging
from .database import Base, SessionLocal, engine, get_db
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
from .routers import connectors_router
from .connectors.manager import connector_manager

configure_logging()
logger = logging.getLogger("mercury.api")
timeline_manager = TimelineManager()


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
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_demo()
    timeline_manager.add_event(
        event_type="mission.started",
        severity="info",
        source="startup",
        message="Mission timeline initialized",
        metadata={"environment": settings.environment},
    )
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


@app.get("/api/v1/integrations")
def integrations():
    return {"version": settings.version, "configured": 12, "online": 9, "sandbox": 3, "simulated": True}


@app.get("/api/v1/compliance")
def compliance():
    return {"version": settings.version, "control_coverage": 92, "open_findings": 4, "certified": False, "simulated": True}


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
