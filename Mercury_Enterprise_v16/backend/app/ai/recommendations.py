from __future__ import annotations

from .models import ThreatLevel


class RecommendationEngine:
    """Generate action recommendations for each threat level."""

    def generate(self, level: ThreatLevel) -> list[str]:
        recommendations = {
            ThreatLevel.LOW: ["Continue monitoring"],
            ThreatLevel.MEDIUM: ["Track target", "Notify operator"],
            ThreatLevel.HIGH: ["Dispatch patrol", "Notify airport operations"],
            ThreatLevel.CRITICAL: ["Immediate response", "Notify all connected agencies"],
        }
        return recommendations[level]
