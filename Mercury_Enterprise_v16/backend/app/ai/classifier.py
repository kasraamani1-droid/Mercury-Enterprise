from __future__ import annotations

from .models import ThreatLevel


class ThreatClassifier:
    """Map a numeric threat score to the requested severity level."""

    def classify(self, score: int) -> ThreatLevel:
        if score >= 90:
            return ThreatLevel.CRITICAL
        if score >= 70:
            return ThreatLevel.HIGH
        if score >= 40:
            return ThreatLevel.MEDIUM
        return ThreatLevel.LOW
