from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class OrchestrationDecision:
    action: str
    severity: str
    reason: str
    mission_id: str | None = None
    track_id: str | None = None
    confidence: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "severity": self.severity,
            "reason": self.reason,
            "mission_id": self.mission_id,
            "track_id": self.track_id,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }
