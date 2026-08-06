from __future__ import annotations

from datetime import datetime, timezone

from ..base import BaseConnector
from ..models import NormalizedObservation


class MockFlightConnector(BaseConnector):
    async def poll(self) -> list[NormalizedObservation]:
        now = datetime.now(timezone.utc)
        return [
            NormalizedObservation(
                source=self.record.id,
                source_type="adsb",
                entity_type="aircraft",
                entity_id="ACA875",
                observed_at=now,
                latitude=45.494,
                longitude=-73.715,
                altitude_m=6705.6,
                speed_kmh=407.4,
                heading_deg=221,
                confidence=0.96,
                attributes={"callsign": "ACA875", "simulated": True},
            ),
            NormalizedObservation(
                source=self.record.id,
                source_type="adsb",
                entity_type="aircraft",
                entity_id="TS742",
                observed_at=now,
                latitude=45.451,
                longitude=-73.781,
                altitude_m=7772.4,
                speed_kmh=472.3,
                heading_deg=64,
                confidence=0.94,
                attributes={"callsign": "TS742", "simulated": True},
            ),
        ]
