from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any

from .models import FusedTrack, Observation, TrackStatus, ThreatLevel


class TrackManager:
    """Thread-safe storage for fused tracks."""

    def __init__(
        self,
        degraded_timeout: int = 120,
        lost_timeout: int = 300,
        max_history: int = 250,
    ) -> None:
        self._tracks: dict[str, FusedTrack] = {}
        self._lock = RLock()
        self.degraded_timeout = degraded_timeout
        self.lost_timeout = lost_timeout
        self.max_history = max_history

    def create_track(self, observation: Observation) -> FusedTrack:
        with self._lock:
            track = FusedTrack(
                target_id=observation.target_id,
                first_seen=observation.timestamp,
                last_seen=observation.timestamp,
                latitude=observation.latitude,
                longitude=observation.longitude,
                altitude=observation.altitude,
                speed=observation.speed,
                heading=observation.heading,
                classification=observation.classification,
                contributing_sensors=[str(observation.sensor_type)],
                observation_count=1,
                metadata={"source": observation.source},
            )
            self._tracks[track.track_id] = track
            return track

    def update_track(self, track: FusedTrack, observation: Observation) -> FusedTrack:
        with self._lock:
            track.last_seen = observation.timestamp
            track.latitude = observation.latitude
            track.longitude = observation.longitude
            track.altitude = observation.altitude
            track.speed = observation.speed
            track.heading = observation.heading
            track.classification = observation.classification
            if str(observation.sensor_type) not in track.contributing_sensors:
                track.contributing_sensors.append(str(observation.sensor_type))
            track.observation_count += 1
            track.metadata.update({"last_source": observation.source})
            return track

    def get_track(self, track_id: str) -> FusedTrack | None:
        with self._lock:
            return self._tracks.get(track_id)

    def get_active_tracks(self) -> list[FusedTrack]:
        with self._lock:
            return [track for track in self._tracks.values() if track.status in {TrackStatus.ACTIVE, TrackStatus.DEGRADED}]

    def mark_degraded(self, track_id: str) -> bool:
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False
            track.status = TrackStatus.DEGRADED
            return True

    def mark_lost(self, track_id: str) -> bool:
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False
            track.status = TrackStatus.LOST
            return True

    def close_track(self, track_id: str) -> bool:
        with self._lock:
            track = self._tracks.get(track_id)
            if track is None:
                return False
            track.status = TrackStatus.CLOSED
            return True

    def remove_expired_tracks(self, now: datetime | None = None) -> list[FusedTrack]:
        if now is None:
            now = datetime.now(timezone.utc)
        removed: list[FusedTrack] = []
        with self._lock:
            expired_ids = []
            for track_id, track in self._tracks.items():
                if track.status in {TrackStatus.CLOSED, TrackStatus.LOST}:
                    continue
                if track.status == TrackStatus.DEGRADED and (now - track.last_seen) > timedelta(seconds=self.lost_timeout):
                    expired_ids.append(track_id)
                elif (now - track.last_seen) > timedelta(seconds=self.lost_timeout + self.degraded_timeout):
                    expired_ids.append(track_id)
            for track_id in expired_ids:
                removed.append(self._tracks.pop(track_id))
        return removed

    def clear(self) -> None:
        with self._lock:
            self._tracks.clear()
