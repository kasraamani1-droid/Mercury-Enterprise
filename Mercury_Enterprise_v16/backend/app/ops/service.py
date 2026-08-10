"""Facade that exposes the orchestration engine through a simple service interface.

Prefer injecting the application-wide `ResponseOrchestrationEngine` from `main`
(via `routers.ops.get_response_orchestrator`) rather than constructing a second engine.
"""

from __future__ import annotations

from typing import Any

from .orchestrator import ResponseOrchestrationEngine


class ResponseOrchestrationService:
    def __init__(self, orchestrator: ResponseOrchestrationEngine | None = None) -> None:
        self.orchestrator = orchestrator or ResponseOrchestrationEngine()

    def coordinate(self, event_type: str, payload: dict[str, Any], source: str = "ops"):
        return self.orchestrator.coordinate(event_type=event_type, payload=payload, source=source)
