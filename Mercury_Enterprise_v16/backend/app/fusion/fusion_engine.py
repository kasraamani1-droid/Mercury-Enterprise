from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any

from .confidence import ConfidenceFusion
from .correlator import CorrelationEngine
from .models import FusedTrack, Observation, ThreatLevel, TrackStatus
from .track_manager import TrackManager


class FusionEngine:
    """Orchestrate sensor observation correlation and track fusion."""

    def __init__(
        self,
        correlation_threshold: float = 0.55,
        degraded_timeout: int = 120,
        lost_timeout: int = 300,
        max_history: int = 250,
    ) -> None:
        self._correlator = CorrelationEngine(threshold=correlation_threshold)
        self._confidence_fusion = ConfidenceFusion()
        self._track_manager = TrackManager(
            degraded_timeout=degraded_timeout,
            lost_timeout=lost_timeout,
            max_history=max_history,
        )
        self._lock = RLock()
        self.correlation_threshold = correlation_threshold
        self.degraded_timeout = degraded_timeout
        self.lost_timeout = lost_timeout
        self.max_history = max_history

    def ingest_observation(self, observation: Observation) -> FusedTrack:
        self._validate_observation(observation)
        with self._lock:
            track = self.create_or_update_track(observation)
            self._track_manager.remove_expired_tracks()
            return track

    def correlate_observation(self, observation: Observation) -> tuple[float, FusedTrack | None]:
        self._validate_observation(observation)
        with self._lock:
            candidate_tracks = self._track_manager.get_active_tracks()
            best_score = 0.0
            best_track: FusedTrack | None = None
            for track in candidate_tracks:
                track_observation = Observation(
                    target_id=track.target_id,
                    timestamp=track.last_seen,
                    latitude=track.latitude,
                    longitude=track.longitude,
                    altitude=track.altitude,
                    speed=track.speed,
                    heading=track.heading,
                    confidence=track.fused_confidence,
                    classification=track.classification,
                    metadata=track.metadata,
                )
                score = self._correlator.correlate(observation, track_observation)
                if score >= self._correlator.threshold and score > best_score:
                    best_score = score
                    best_track = track
            return best_score, best_track

    def create_or_update_track(self, observation: Observation) -> FusedTrack:
        score, track = self.correlate_observation(observation)
        if track is None or score < self._correlator.threshold:
            track = self._track_manager.create_track(observation)
        else:
            track = self._track_manager.update_track(track, observation)

        observations = self._get_observations_for_track(track)
        track.fused_confidence = self._confidence_fusion.fuse(observations)
        track.threat_score = self._calculate_threat_score(track)
        track.threat_level = self._classify_threat(track.threat_score)
        track.status = self._determine_status(track)
        return track

    def get_tracks(self) -> list[FusedTrack]:
        return self._track_manager.get_active_tracks()

    def get_track(self, track_id: str) -> FusedTrack | None:
        return self._track_manager.get_track(track_id)

    def clear(self) -> None:
        self._track_manager.clear()

    def _validate_observation(self, observation: Observation) -> None:
        if not observation.target_id:
            raise ValueError("target_id is required")
        if observation.confidence < 0.0 or observation.confidence > 100.0:
            raise ValueError("confidence must be between 0 and 100")
        if not str(observation.sensor_type):
            raise ValueError("sensor_type is required")

    def _get_observations_for_track(self, track: FusedTrack) -> list[Observation]:
        return [
            Observation(
                target_id=track.target_id,
                timestamp=track.last_seen,
                latitude=track.latitude,
                longitude=track.longitude,
                altitude=track.altitude,
                speed=track.speed,
                heading=track.heading,
                confidence=track.fused_confidence,
                classification=track.classification,
                metadata=track.metadata,
            )
        ]

    def _calculate_threat_score(self, track: FusedTrack) -> float:
        return min(100.0, track.fused_confidence + (track.observation_count * 2.0))

    def _classify_threat(self, threat_score: float) -> ThreatLevel:
        if threat_score >= 90:
            return ThreatLevel.CRITICAL
        if threat_score >= 70:
            return ThreatLevel.HIGH
        if threat_score >= 40:
            return ThreatLevel.MEDIUM
        return ThreatLevel.LOW

    def _determine_status(self, track: FusedTrack) -> TrackStatus:
        if track.observation_count >= 3:
            return TrackStatus.ACTIVE
        if track.observation_count == 2:
            return TrackStatus.DEGRADED
        return TrackStatus.ACTIVE
