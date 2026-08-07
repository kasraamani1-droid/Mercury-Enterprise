from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from typing import Any

from ..ai import ThreatRiskEngine
from ..alerts import AlertManager
from ..core.event_bus import EventBus, event_bus
from ..fusion import FusionEngine
from ..missions import MissionPriority, MissionService
from ..ops import ResponseOrchestrationEngine
from ..timeline import TimelineManager
from .explanations import DecisionExplanationEngine
from .models import DecisionCandidate, DecisionResult
from .scoring import DecisionScoringEngine

logger = logging.getLogger("mercury.decision.engine")


class DecisionEngine:
    """Produce deterministic, explainable decision recommendations using existing backend services."""

    def __init__(
        self,
        event_bus_instance: EventBus | None = None,
        timeline_manager: TimelineManager | None = None,
        mission_service: MissionService | None = None,
        threat_engine: ThreatRiskEngine | None = None,
        fusion_engine: FusionEngine | None = None,
        alert_manager: AlertManager | None = None,
        response_orchestrator: ResponseOrchestrationEngine | None = None,
    ) -> None:
        self._event_bus = event_bus_instance or event_bus
        self._timeline_manager = timeline_manager or TimelineManager(event_bus_instance=self._event_bus)
        self._mission_service = mission_service or MissionService()
        self._threat_engine = threat_engine or ThreatRiskEngine()
        self._fusion_engine = fusion_engine or FusionEngine()
        self._alert_manager = alert_manager or AlertManager(event_bus_instance=self._event_bus)
        self._response_orchestrator = response_orchestrator or ResponseOrchestrationEngine(
            event_bus_instance=self._event_bus,
            timeline_manager=self._timeline_manager,
            mission_service=self._mission_service,
            threat_engine=self._threat_engine,
            fusion_engine=self._fusion_engine,
        )
        self._scoring_engine = DecisionScoringEngine()
        self._explanation_engine = DecisionExplanationEngine()

    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        normalized_context = self._normalize_context(context)
        self.validate_context(normalized_context)

        self._publish_event("decision.requested", normalized_context)

        mission = self._resolve_mission(normalized_context)
        mission_context = self._build_mission_context(mission, normalized_context)
        fused_context = self._resolve_fusion_context(normalized_context)
        alert_context = self._resolve_alert_context(normalized_context)

        enriched_context = deepcopy(normalized_context)
        enriched_context.update(mission_context)
        enriched_context.update(fused_context)
        enriched_context.update(alert_context)

        recommendations = self._collect_recommendations(enriched_context)
        ranked_actions = [self._score_candidate(action, enriched_context) for action in recommendations]
        ranked_actions.sort(key=lambda item: item.overall_score, reverse=True)

        selected = ranked_actions[0] if ranked_actions else self._fallback_candidate(enriched_context)
        reasoning, warnings = self._explanation_engine.explain(enriched_context, [action.to_dict() for action in ranked_actions], selected.to_dict())

        result = DecisionResult(
            mission_id=enriched_context.get("mission_id"),
            track_id=enriched_context.get("track_id"),
            context_summary=self._build_context_summary(enriched_context),
            ranked_actions=ranked_actions,
            selected_recommendation=selected,
            confidence=self._calculate_confidence(ranked_actions, selected),
            reasoning=reasoning,
            warnings=warnings,
            requires_human_approval=True,
            metadata={
                "automatic_execution": False,
                "source": "decision_engine",
                "threat_level": enriched_context.get("threat_level"),
                "mission_priority": enriched_context.get("mission_priority"),
            },
        )

        self._publish_event("decision.evaluated", result.to_dict())
        self._publish_event("decision.recommendation_selected", result.to_dict())

        return result.to_dict()

    def rank_actions(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        normalized_context = self._normalize_context(context)
        self.validate_context(normalized_context)
        recommendations = self._collect_recommendations(normalized_context)
        ranked_actions = [self._score_candidate(action, normalized_context) for action in recommendations]
        ranked_actions.sort(key=lambda item: item.overall_score, reverse=True)
        return [action.to_dict() for action in ranked_actions]

    def select_recommendation(self, context: dict[str, Any]) -> dict[str, Any]:
        ranked = self.rank_actions(context)
        return ranked[0] if ranked else self._fallback_candidate(self._normalize_context(context)).to_dict()

    def explain(self, context: dict[str, Any]) -> dict[str, Any]:
        normalized_context = self._normalize_context(context)
        self.validate_context(normalized_context)
        ranked = self.rank_actions(normalized_context)
        selected = self.select_recommendation(normalized_context)
        reasoning, warnings = self._explanation_engine.explain(normalized_context, ranked, selected)
        return {"reasoning": reasoning, "warnings": warnings, "selected_recommendation": selected}

    def validate_context(self, context: dict[str, Any]) -> None:
        if not isinstance(context, dict):
            raise ValueError("Context must be a dictionary")
        if not context.get("mission_id"):
            raise ValueError("mission_id is required")
        if not context.get("track_id"):
            raise ValueError("track_id is required")
        if not context.get("threat_score") and not context.get("threat_level"):
            raise ValueError("threat_score or threat_level is required")

    def _normalize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(context or {})
        normalized.setdefault("mission_id", None)
        normalized.setdefault("track_id", None)
        normalized.setdefault("threat_score", 0.0)
        normalized.setdefault("threat_level", "low")
        normalized.setdefault("threat_confidence", normalized.get("fused_confidence", 0.0))
        normalized.setdefault("mission_status", "active")
        normalized.setdefault("mission_priority", "normal")
        normalized.setdefault("active_alerts", [])
        normalized.setdefault("available_resources", [])
        normalized.setdefault("fused_confidence", 0.0)
        normalized.setdefault("response_recommendations", [])
        normalized.setdefault("operator_constraints", [])
        normalized.setdefault("environmental_context", {})
        normalized.setdefault("metadata", {})
        normalized["mission_priority"] = str(normalized.get("mission_priority") or "normal").lower()
        normalized["threat_level"] = str(normalized.get("threat_level") or "low").lower()
        return normalized

    def _resolve_mission(self, context: dict[str, Any]) -> Any | None:
        mission_id = context.get("mission_id")
        if not mission_id:
            return None
        return self._mission_service.get_mission(str(mission_id))

    def _build_mission_context(self, mission: Any | None, context: dict[str, Any]) -> dict[str, Any]:
        if mission is None:
            return {}
        return {
            "mission_priority": str(mission.priority.value).lower() if getattr(mission, "priority", None) else context.get("mission_priority"),
            "mission_status": str(mission.status.value).lower() if getattr(mission, "status", None) else context.get("mission_status"),
            "assigned_resources": getattr(mission, "assigned_resources", []),
            "operator_constraints": list(getattr(mission, "metadata", {}).get("constraints", []) or []),
        }

    def _resolve_fusion_context(self, context: dict[str, Any]) -> dict[str, Any]:
        track_id = context.get("track_id")
        if not track_id:
            return {}
        track = self._fusion_engine.get_track(str(track_id))
        if track is None:
            return {}
        return {
            "fused_confidence": float(getattr(track, "fused_confidence", 0.0) or 0.0),
            "threat_level": str(getattr(track, "threat_level", "low")).lower(),
            "threat_score": float(getattr(track, "threat_score", 0.0) or 0.0),
        }

    def _resolve_alert_context(self, context: dict[str, Any]) -> dict[str, Any]:
        alerts = self._alert_manager.get_alerts(limit=10)
        if not alerts:
            return {"active_alerts": []}
        return {"active_alerts": [alert.to_dict() for alert in alerts]}

    def _collect_recommendations(self, context: dict[str, Any]) -> list[str]:
        response_recommendations = context.get("response_recommendations") or []
        if response_recommendations:
            return [str(item) for item in response_recommendations]

        assessment = self._threat_engine.assess(float(context.get("threat_score") or 0.0), float(context.get("threat_confidence") or 0.0))
        return assessment.recommendations

    def _score_candidate(self, action: str, context: dict[str, Any]) -> DecisionCandidate:
        return self._scoring_engine.score(action, context)

    def _fallback_candidate(self, context: dict[str, Any]) -> DecisionCandidate:
        return self._score_candidate("Monitor current state", context)

    def _build_context_summary(self, context: dict[str, Any]) -> str:
        mission = context.get("mission_id") or "unknown"
        track = context.get("track_id") or "unknown"
        threat = context.get("threat_level") or "low"
        priority = context.get("mission_priority") or "normal"
        return f"Mission {mission} track {track} threat {threat} priority {priority}"

    def _calculate_confidence(self, ranked_actions: list[DecisionCandidate], selected: DecisionCandidate) -> float:
        if not ranked_actions:
            return 0.0
        margin = max(0.0, ranked_actions[0].overall_score - (ranked_actions[1].overall_score if len(ranked_actions) > 1 else 0.0))
        return round(min(100.0, 60.0 + (margin * 0.35) + selected.feasibility_score * 0.1), 2)

    def _publish_event(self, event_name: str, payload: dict[str, Any]) -> None:
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                loop.create_task(self._event_bus.publish(event_name, payload, source="decision_engine"))
            else:
                asyncio.run(self._event_bus.publish(event_name, payload, source="decision_engine"))
        except Exception:
            logger.exception("Failed to publish decision event event=%s", event_name)
