from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from time import perf_counter

from .models import ConnectorHealth, ConnectorRecord, ConnectorState, NormalizedObservation


class BaseConnector(ABC):
    def __init__(self, record: ConnectorRecord) -> None:
        self.record = record

    async def start(self) -> None:
        self.record.state = ConnectorState.starting
        self.record.last_transition_at = datetime.now(timezone.utc)
        self.record.state = ConnectorState.online
        self.record.last_error = None
        self.record.last_transition_at = datetime.now(timezone.utc)

    async def stop(self) -> None:
        self.record.state = ConnectorState.offline
        self.record.last_error = None
        self.record.last_transition_at = datetime.now(timezone.utc)

    async def recover(self) -> None:
        self.record.retry_count = 0
        self.record.last_error = None
        await self.start()

    @abstractmethod
    async def poll(self) -> list[NormalizedObservation]:
        raise NotImplementedError

    async def health(self) -> ConnectorHealth:
        # latency_ms measures local health-evaluation duration only (not remote RTT).
        # APPLY_TASK_18 / Milestone 1 require diagnosability via state, history, and errors;
        # they do not require probing remote connector latency. Mock providers have no RTT.
        started = perf_counter()
        payload: dict = {
            "connector_id": self.record.id,
            "state": self.record.state,
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "retry_count": self.record.retry_count,
            "last_error": self.record.last_error,
            "last_transition_at": self.record.last_transition_at,
        }
        if self.record.state == ConnectorState.degraded:
            payload["message"] = self.record.last_error or "connector degraded"
        elif self.record.state == ConnectorState.error:
            payload["message"] = self.record.last_error or "connector error"
        elif self.record.state != ConnectorState.online:
            payload["message"] = f"connector {self.record.state.value}"
        # online: omit message so ConnectorHealth default ("ok") applies
        return ConnectorHealth(**payload)
