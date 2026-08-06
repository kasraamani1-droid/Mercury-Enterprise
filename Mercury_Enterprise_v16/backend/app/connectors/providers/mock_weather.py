from __future__ import annotations

from datetime import datetime, timezone

from ..base import BaseConnector
from ..models import NormalizedObservation


class MockWeatherConnector(BaseConnector):
    async def poll(self) -> list[NormalizedObservation]:
        return [
            NormalizedObservation(
                source=self.record.id,
                source_type="weather",
                entity_type="weather_station",
                entity_id="CYUL-MET",
                observed_at=datetime.now(timezone.utc),
                latitude=45.4706,
                longitude=-73.7408,
                confidence=0.99,
                attributes={
                    "wind_kmh": 18,
                    "visibility_km": 24,
                    "temperature_c": 12,
                    "pressure_hpa": 1014,
                    "simulated": True,
                },
            )
        ]
