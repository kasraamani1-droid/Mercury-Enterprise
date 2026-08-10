from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from ..ai import ThreatRiskEngine
from ..alerts import AlertManager
from ..core.event_bus import EventBus, event_bus
from ..fusion import FusionEngine
from ..missions import MissionService
from ..ops import ResponseOrchestrationEngine
from ..timeline import TimelineManager
from .explanations import DecisionExplanationEngine
from .models import DecisionCandidate, DecisionResult
from .scoring import DecisionScoringEngine

logger = logging.getLogger("mercury.decision.engine")

_REVIEW_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"acknowledged", "commented", "rejected_advisory"},
    "commented": {"acknowledged"},
}

_TERMINAL_REVIEW_STATES = {"acknowledged", "rejected_advisory"}
_MAX_DECISION_STORE = 200


def build_connector_context(connector_manager: Any | None) -> dict[str, Any]:
    if connector_manager is None:
        return {"degraded": [], "error": [], "online": 0, "total": 0}
    try:
        records = list(connector_manager.list_records())
    except Exception:
        return {"degraded": [], "error": [], "online": 0, "total": 0}
    degraded: list[str] = []
    error: list[str] = []
    online = 0
    for record in records:
        state = str(getattr(getattr(record, "state", None), "value", getattr(record, "state", "")) or "").lower()
        connector_id = str(getattr(record, "id", "") or "")
        if state == "online":
            online += 1
        elif state == "degraded" and connector_id:
            degraded.append(connector_id)
        elif state == "error" and connector_id:
            error.append(connector_id)
    return {
        "degraded": degraded,
        "error": error,
        "online": online,
        "total": len(records),
    }


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
        connector_manager: Any | None = None,
        max_store: int = _MAX_DECISION_STORE,
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
        self._connector_manager = connector_manager
        self._max_store = max(1, int(max_store))
        self._decision_store: OrderedDict[str, dict[str, Any]] = OrderedDict()

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
        explanation = self._explanation_engine.explain(
            enriched_context,
            [action.to_dict() for action in ranked_actions],
            selected.to_dict(),
        )
        connector_context = build_connector_context(self._connector_manager)
        if connector_context.get("degraded") or connector_context.get("error"):
            explanation["warnings"] = list(explanation.get("warnings") or [])
            explanation["warnings"].append(
                "One or more connectors are degraded or in error; interpret recommendations with reduced trust."
            )

        result = DecisionResult(
            mission_id=enriched_context.get("mission_id"),
            track_id=enriched_context.get("track_id"),
            context_summary=self._build_context_summary(enriched_context),
            ranked_actions=ranked_actions,
            selected_recommendation=selected,
            confidence=self._calculate_confidence(ranked_actions, selected),
            reasoning=str(explanation.get("reasoning") or ""),
            warnings=list(explanation.get("warnings") or []),
            assumptions=list(explanation.get("assumptions") or []),
            uncertainty=list(explanation.get("uncertainty") or []),
            factor_breakdown=list(explanation.get("factor_breakdown") or []),
            evidence_links=list(explanation.get("evidence_links") or []),
            connector_context=connector_context,
            organization_id=enriched_context.get("organization_id"),
            site_id=enriched_context.get("site_id"),
            requires_human_approval=True,
            metadata={
                "automatic_execution": False,
                "advisory_only": True,
                "source": "decision_engine",
                "threat_level": enriched_context.get("threat_level"),
                "mission_priority": enriched_context.get("mission_priority"),
            },
        )

        payload = result.to_dict()
        self._store_decision(payload)
        self._publish_event("decision.evaluated", payload)
        self._publish_event("decision.recommendation_selected", payload)
        return payload

    def get_decision(self, decision_id: str, organization_id: str | None = None, site_id: str | None = None) -> dict[str, Any] | None:
        payload = self._decision_store.get(decision_id)
        if payload is None:
            return None
        if organization_id is not None and payload.get("organization_id") != organization_id:
            return None
        if site_id is not None and payload.get("site_id") != site_id:
            return None
        return deepcopy(payload)

    def list_decisions(
        self,
        organization_id: str | None = None,
        site_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        capped = max(1, min(int(limit), 100))
        items: list[dict[str, Any]] = []
        for payload in reversed(list(self._decision_store.values())):
            if organization_id is not None and payload.get("organization_id") != organization_id:
                continue
            if site_id is not None and payload.get("site_id") != site_id:
                continue
            items.append(deepcopy(payload))
            if len(items) >= capped:
                break
        return items

    def apply_review(
        self,
        decision_id: str,
        state: str,
        comment: str | None,
        actor: str,
        organization_id: str | None = None,
        site_id: str | None = None,
    ) -> dict[str, Any]:
        payload = self.get_decision(decision_id, organization_id=organization_id, site_id=site_id)
        if payload is None:
            raise KeyError("decision_not_found")

        current_state = str((payload.get("review") or {}).get("state") or "pending")
        next_state = str(state or "").strip().lower()
        allowed = _REVIEW_TRANSITIONS.get(current_state, set())
        if next_state not in allowed:
            raise ValueError("invalid_review_transition")
        if next_state == "commented" and not str(comment or "").strip():
            raise ValueError("comment_required")

        review = {
            "state": next_state,
            "comment": (str(comment).strip() if comment is not None and str(comment).strip() else None),
            "reviewed_by": actor,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        payload["review"] = review
        self._decision_store[decision_id] = payload
        self._decision_store.move_to_end(decision_id)
        self._publish_event("decision.reviewed", payload)
        return deepcopy(payload)

    def pending_review_count(self, organization_id: str | None = None, site_id: str | None = None) -> int:
        return sum(
            1
            for item in self.list_decisions(organization_id=organization_id, site_id=site_id, limit=100)
            if str((item.get("review") or {}).get("state") or "") == "pending"
        )

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
        explanation = self._explanation_engine.explain(normalized_context, ranked, selected)
        return {
            "reasoning": explanation.get("reasoning"),
            "warnings": explanation.get("warnings"),
            "assumptions": explanation.get("assumptions"),
            "uncertainty": explanation.get("uncertainty"),
            "factor_breakdown": explanation.get("factor_breakdown"),
            "evidence_links": explanation.get("evidence_links"),
            "selected_recommendation": selected,
        }

    def validate_context(self, context: dict[str, Any]) -> None:
        if not isinstance(context, dict):
            raise ValueError("Context must be a dictionary")
        if not context.get("mission_id"):
            raise ValueError("mission_id is required")
        if not context.get("track_id"):
            raise ValueError("track_id is required")
        if not context.get("threat_score") and not context.get("threat_level"):
            raise ValueError("threat_score or threat_level is required")

    def _store_decision(self, payload: dict[str, Any]) -> None:
        decision_id = str(payload.get("decision_id") or "")
        if not decision_id:
            return
        self._decision_store[decision_id] = deepcopy(payload)
        self._decision_store.move_to_end(decision_id)
        while len(self._decision_store) > self._max_store:
            self._decision_store.popitem(last=False)

    def _normalize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(context or {})
        normalized.setdefault("mission_id", None)
        normalized.setdefault("track_id", None)
        if normalized.get("threat_score") is None:
            normalized["threat_score"] = 0.0
        if not normalized.get("threat_level"):
            normalized["threat_level"] = "low"
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
        normalized.setdefault("organization_id", None)
        normalized.setdefault("site_id", None)
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
