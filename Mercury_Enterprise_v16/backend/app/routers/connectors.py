from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..connectors.manager import connector_manager
from ..connectors.models import ConnectorHealth, ConnectorRecord, NormalizedObservation
from ..events.bus import event_bus
from ..events.models import PlatformEvent

router = APIRouter(prefix="/api/v1", tags=["Connectors"])


@router.get("/connectors", response_model=list[ConnectorRecord])
def list_connectors():
    return connector_manager.list_records()


@router.get("/connectors/{connector_id}/health", response_model=ConnectorHealth)
async def connector_health(connector_id: str):
    connector = connector_manager.get(connector_id)
    if connector is None:
        raise HTTPException(404, "Connector not found")
    return await connector.health()


@router.post("/connectors/{connector_id}/poll", response_model=list[NormalizedObservation])
async def poll_connector(connector_id: str):
    try:
        return await connector_manager.poll(connector_id)
    except KeyError as exc:
        raise HTTPException(404, "Connector not found") from exc


@router.get("/events", response_model=list[PlatformEvent])
def recent_events(limit: int = Query(default=50, ge=1, le=500)):
    return event_bus.recent(limit)
