from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ConnectorState(str, Enum):
    offline = "offline"
    starting = "starting"
    online = "online"
    degraded = "degraded"
    error = "error"


class ConnectorRecord(BaseModel):
    id: str
    name: str
    provider: str
    category: str
    state: ConnectorState = ConnectorState.offline
    enabled: bool = True
    simulated: bool = True
    last_poll_at: datetime | None = None
    last_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorHealth(BaseModel):
    connector_id: str
    state: ConnectorState
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float | None = None
    message: str = "ok"


class NormalizedObservation(BaseModel):
    observation_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    source_type: str
    entity_type: str
    entity_id: str
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    speed_kmh: float | None = None
    heading_deg: float | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    attributes: dict[str, Any] = Field(default_factory=dict)
