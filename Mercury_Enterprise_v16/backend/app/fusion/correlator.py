from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from .models import Observation


class CorrelationEngine:
    """Correlate observations into a likely common track."""

    def __init__(self, threshold: float = 0.55) -> None:
        self.threshold = threshold

    def correlate(self, observation: Observation, candidate: Observation) -> float:
        if observation.target_id and candidate.target_id and observation.target_id != candidate.target_id:
            return 0.0

        score = 0.0
        if observation.target_id and candidate.target_id and observation.target_id == candidate.target_id:
            score += 0.25

        distance_score = self._distance_score(observation, candidate)
        time_score = self._time_score(observation, candidate)
        altitude_score = self._altitude_score(observation, candidate)
        speed_score = self._speed_score(observation, candidate)
        heading_score = self._heading_score(observation, candidate)
        classification_score = self._classification_score(observation, candidate)

        score += distance_score * 0.25
        score += time_score * 0.2
        score += altitude_score * 0.15
        score += speed_score * 0.15
        score += heading_score * 0.1
        score += classification_score * 0.1

        return max(0.0, min(1.0, score))

    def _distance_score(self, observation: Observation, candidate: Observation) -> float:
        distance_km = self._haversine_km(observation.latitude, observation.longitude, candidate.latitude, candidate.longitude)
        if distance_km <= 2.0:
            return 1.0
        if distance_km <= 10.0:
            return max(0.0, 1.0 - ((distance_km - 2.0) / 8.0))
        return 0.0

    def _time_score(self, observation: Observation, candidate: Observation) -> float:
        delta_seconds = abs((observation.timestamp - candidate.timestamp).total_seconds())
        if delta_seconds <= 30:
            return 1.0
        if delta_seconds <= 180:
            return max(0.0, 1.0 - ((delta_seconds - 30) / 150.0))
        return 0.0

    def _altitude_score(self, observation: Observation, candidate: Observation) -> float:
        delta = abs(observation.altitude - candidate.altitude)
        if delta <= 50:
            return 1.0
        if delta <= 200:
            return max(0.0, 1.0 - ((delta - 50) / 150.0))
        return 0.0

    def _speed_score(self, observation: Observation, candidate: Observation) -> float:
        delta = abs(observation.speed - candidate.speed)
        if delta <= 10:
            return 1.0
        if delta <= 40:
            return max(0.0, 1.0 - ((delta - 10) / 30.0))
        return 0.0

    def _heading_score(self, observation: Observation, candidate: Observation) -> float:
        delta = abs((observation.heading - candidate.heading) % 360)
        if delta <= 20:
            return 1.0
        if delta <= 90:
            return max(0.0, 1.0 - ((delta - 20) / 70.0))
        return 0.0

    def _classification_score(self, observation: Observation, candidate: Observation) -> float:
        if not observation.classification or not candidate.classification:
            return 0.5
        if observation.classification.lower() == candidate.classification.lower():
            return 1.0
        return 0.3

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_km = 6371.0
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius_km * c
