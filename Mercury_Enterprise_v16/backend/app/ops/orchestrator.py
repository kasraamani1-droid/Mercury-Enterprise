from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..ai import ThreatRiskEngine
from ..core.event_bus import EventBus, event_bus
from ..fusion import FusionEngine
from ..missions import MissionPriority, MissionService
from ..timeline import TimelineManager
from .models import OrchestrationDecision

logger = logging.getLogger("mercury.ops.orchestrator")


class ResponseOrchestrationEngine:
    """Coordinate existing backend outputs into response actions without duplicating their logic."""

    def __init__(
        self,
        event_bus_instance: EventBus | None = None,
        timeline_manager: TimelineManager | None = None,
        mission_service: MissionService | None = None,
        threat_engine: ThreatRiskEngine | None = None,
        fusion_engine: FusionEngine | None = None,
    ) -> None:
        self._event_bus = event_bus_instance or event_bus
        self._timeline_manager = timeline_manager or TimelineManager(event_bus_instance=self._event_bus)
        self._mission_service = mission_service or MissionService()
        self._threat_engine = threat_engine or ThreatRiskEngine()
        self._fusion_engine = fusion_engine or FusionEngine()

    def coordinate(self, event_type: str, payload: dict[str, Any], source: str = "ops") -> OrchestrationDecision:
        if payload is None:
            payload = {}

        decision = self._build_decision(event_type, payload)

        self._publish_event("ops.orchestrated", {
            "action": decision.action,
            "severity": decision.severity,
            "reason": decision.reason,
            "mission_id": decision.mission_id,
            "track_id": decision.track_id,
            "confidence": decision.confidence,
            "source": source,
            "event_type": event_type,
        })

        if decision.action == "escalate":
            self._publish_event("ops.escalation", {
                "action": decision.action,
                "severity": decision.severity,
                "reason": decision.reason,
                "mission_id": decision.mission_id,
                "track_id": decision.track_id,
                "confidence": decision.confidence,
                "source": source,
                "event_type": event_type,
            })

        return decision

    def _publish_event(self, event_name: str, payload: dict[str, Any]) -> None:
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                loop.create_task(self._event_bus.publish(event_name, payload, source="response_orchestrator"))
            else:
                asyncio.run(self._event_bus.publish(event_name, payload, source="response_orchestrator"))
        except Exception:
            logger.exception("Failed to publish orchestration event event=%s", event_name)

    def _build_decision(self, event_type: str, payload: dict[str, Any]) -> OrchestrationDecision:
        mission_id = payload.get("mission_id")
        track_id = payload.get("track_id")
        confidence = payload.get("confidence")
        fused_confidence = payload.get("fused_confidence")
        threat_level = payload.get("threat_level")
        level = payload.get("level")

        mission = self._mission_service.get_mission(str(mission_id)) if mission_id else None
        if track_id:
            track = self._fusion_engine.get_track(track_id)
            if track is not None and getattr(track, "threat_level", None) is not None:
                normalized_level = str(track.threat_level).lower()
                if normalized_level in {"high", "critical"}:
                    return OrchestrationDecision(
                        action="escalate",
                        severity="high",
                        reason="Existing fused track threat level required escalation",
                        mission_id=mission_id,
                        track_id=track_id,
                        confidence=float(getattr(track, "threat_score", 0.0) or 0.0),
                    )

        if fused_confidence is not None:
            score = float(fused_confidence)
            threshold = 90.0
            if mission is not None and mission.priority in {MissionPriority.HIGH, MissionPriority.CRITICAL}:
                threshold = 80.0
            if score >= threshold:
                return OrchestrationDecision(
                    action="escalate",
                    severity="high",
                    reason="High-confidence fusion output exceeded escalation threshold",
                    mission_id=mission_id,
                    track_id=track_id,
                    confidence=score,
                )
            if score >= (70.0 if mission is None or mission.priority not in {MissionPriority.HIGH, MissionPriority.CRITICAL} else 60.0):
                return OrchestrationDecision(
                    action="alert",
                    severity="medium",
                    reason="Fusion output reached alert threshold",
                    mission_id=mission_id,
                    track_id=track_id,
                    confidence=score,
                )

        if confidence is not None:
            assessment = self._threat_engine.assess(float(confidence), 50.0)
            if assessment.level.value.lower() in {"high", "critical"}:
                return OrchestrationDecision(
                    action="escalate",
                    severity="high",
                    reason="AI threat assessment reached an elevated threat level",
                    mission_id=mission_id,
                    track_id=track_id,
                    confidence=float(confidence),
                )

        if threat_level is not None:
            normalized = str(threat_level).lower()
            if normalized in {"high", "critical"}:
                return OrchestrationDecision(
                    action="escalate",
                    severity="high",
                    reason="Threat level from fusion output required escalation",
                    mission_id=mission_id,
                    track_id=track_id,
                    confidence=fused_confidence,
                )

        if level is not None:
            normalized = str(level).lower()
            if normalized in {"high", "critical"}:
                return OrchestrationDecision(
                    action="alert",
                    severity="medium",
                    reason="AI level indicated a significant risk",
                    mission_id=mission_id,
                    track_id=track_id,
                    confidence=float(confidence or 0.0),
                )

        return OrchestrationDecision(
            action="monitor",
            severity="info",
            reason="No escalation criteria met; monitoring the current state",
            mission_id=mission_id,
            track_id=track_id,
            confidence=float(confidence or fused_confidence or 0.0),
        )
