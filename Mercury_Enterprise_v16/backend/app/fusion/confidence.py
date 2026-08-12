from __future__ import annotations

from datetime import datetime, timezone

from .models import Observation


class ConfidenceFusion:
    """Merge individual observation confidence into a fused confidence score."""

    def __init__(self, freshness_window_seconds: int = 300) -> None:
        self.freshness_window_seconds = freshness_window_seconds

    def fuse(self, observations: list[Observation]) -> float:
        if not observations:
            return 0.0

        avg_confidence = sum(obs.confidence for obs in observations) / len(observations)
        sensor_diversity = len({str(obs.sensor_type).lower() for obs in observations})
        independent_sensors = min(sensor_diversity, 5)
        freshness_score = self._freshness_score(observations)
        agreement_score = self._agreement_score(observations)

        fused = (
            avg_confidence * 0.45
            + independent_sensors * 5.0 * 0.2
            + freshness_score * 0.2
            + agreement_score * 0.15
        )
        return max(0.0, min(100.0, fused))

    def _freshness_score(self, observations: list[Observation]) -> float:
        now = datetime.now(timezone.utc)
        scores = []
        for observation in observations:
            age_seconds = max(0.0, (now - observation.timestamp).total_seconds())
            if age_seconds <= self.freshness_window_seconds:
                scores.append(max(0.0, 1.0 - (age_seconds / self.freshness_window_seconds)))
            else:
                scores.append(0.0)
        return sum(scores) / len(scores) * 100.0 if scores else 0.0

    def _agreement_score(self, observations: list[Observation]) -> float:
        if len(observations) < 2:
            return 100.0
        classifications = {obs.classification.lower() for obs in observations if obs.classification}
        if len(classifications) == 1:
            return 100.0
        return 60.0
