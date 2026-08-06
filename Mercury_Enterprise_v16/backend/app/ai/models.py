from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ThreatLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(slots=True)
class ThreatAssessmentResult:
    score: int
    confidence: int
    level: ThreatLevel
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "confidence": self.confidence,
            "level": self.level.value,
            "recommendations": self.recommendations,
        }
