from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class SensorType(StrEnum):
    RF = "RF"
    RADAR = "RADAR"
    CAMERA = "CAMERA"
    THERMAL = "THERMAL"
    ADSB = "ADSB"
    MANUAL = "MANUAL"
    SIMULATION = "SIMULATION"


class TrackStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    LOST = "LOST"
    CLOSED = "CLOSED"


class ThreatLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(slots=True)
class Observation:
    observation_id: str = field(default_factory=lambda: str(uuid4()))
    source: str = "mercury"
    sensor_type: SensorType | str = SensorType.SIMULATION
    target_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    speed: float = 0.0
    heading: float = 0.0
    confidence: float = 0.0
    classification: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "source": self.source,
            "sensor_type": str(self.sensor_type),
            "target_id": self.target_id,
            "timestamp": self.timestamp.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "speed": self.speed,
            "heading": self.heading,
            "confidence": self.confidence,
            "classification": self.classification,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class FusedTrack:
    track_id: str = field(default_factory=lambda: str(uuid4()))
    target_id: str = ""
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    speed: float = 0.0
    heading: float = 0.0
    classification: str = "unknown"
    fused_confidence: float = 0.0
    threat_score: float = 0.0
    threat_level: ThreatLevel = ThreatLevel.LOW
    contributing_sensors: list[str] = field(default_factory=list)
    observation_count: int = 0
    status: TrackStatus = TrackStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "target_id": self.target_id,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "speed": self.speed,
            "heading": self.heading,
            "classification": self.classification,
            "fused_confidence": self.fused_confidence,
            "threat_score": self.threat_score,
            "threat_level": self.threat_level.value,
            "contributing_sensors": self.contributing_sensors,
            "observation_count": self.observation_count,
            "status": self.status.value,
            "metadata": self.metadata,
        }
