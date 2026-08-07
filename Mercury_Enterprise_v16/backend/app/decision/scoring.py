from __future__ import annotations

from typing import Any

from .models import DecisionCandidate


class DecisionScoringEngine:
    """Score candidate actions deterministically using operational context."""

    def score(self, action_name: str, context: dict[str, Any]) -> DecisionCandidate:
        threat_score = float(context.get("threat_score") or 0.0)
        threat_confidence = float(context.get("threat_confidence") or context.get("fused_confidence") or 0.0)
        fused_confidence = float(context.get("fused_confidence") or 0.0)
        mission_priority = str(context.get("mission_priority") or "normal").lower()
        active_alerts = context.get("active_alerts") or []
        available_resources = context.get("available_resources") or []
        operator_constraints = context.get("operator_constraints") or []
        response_recommendations = context.get("response_recommendations") or []
        threat_level = str(context.get("threat_level") or "low").lower()

        severity_component = self._severity_component(threat_score, threat_level)
        confidence_component = self._clamp(100.0 * (threat_confidence / 100.0))
        mission_component = self._mission_component(mission_priority)
        resource_component = self._resource_component(available_resources, action_name)
        feasibility_component = self._feasibility_component(action_name, available_resources, operator_constraints)
        risk_component = self._risk_component(active_alerts, operator_constraints, action_name)
        mission_alignment = self._mission_alignment(action_name, mission_priority, response_recommendations)

        overall_score = (
            severity_component * 0.30
            + confidence_component * 0.20
            + mission_component * 0.20
            + feasibility_component * 0.15
            + resource_component * 0.10
            + mission_alignment * 0.05
        )

        if fused_confidence >= 90.0:
            overall_score += 3.0
        if active_alerts:
            overall_score += 2.0
        if threat_level in {"high", "critical"}:
            overall_score += 2.0

        overall_score = self._clamp(overall_score)
        reasons = [
            f"Threat severity contributed {severity_component:.0f} points.",
            f"Response confidence contributed {confidence_component:.0f} points.",
            f"Mission priority contributed {mission_component:.0f} points.",
        ]
        if active_alerts:
            reasons.append("Active alerts increased urgency.")
        if operator_constraints:
            reasons.append("Operator constraints were considered.")

        return DecisionCandidate(
            name=action_name,
            category=self._category_for_name(action_name),
            description=f"Recommended action based on current threat and mission context: {action_name}",
            source_module="decision_engine",
            priority=self._priority_for_name(action_name),
            confidence=confidence_component,
            feasibility_score=feasibility_component,
            risk_score=risk_component,
            mission_alignment_score=mission_alignment,
            resource_impact_score=resource_component,
            overall_score=overall_score,
            reasons=reasons,
            constraints=list(operator_constraints),
            metadata={"threat_score": threat_score, "threat_level": threat_level, "mission_priority": mission_priority},
        )

    def _severity_component(self, threat_score: float, threat_level: str) -> float:
        level_bonus = {"low": 0.0, "medium": 10.0, "high": 20.0, "critical": 30.0}.get(threat_level, 0.0)
        return self._clamp(threat_score * 0.7 + level_bonus)

    def _mission_component(self, mission_priority: str) -> float:
        weights = {"low": 40.0, "normal": 55.0, "high": 75.0, "critical": 90.0}
        return weights.get(mission_priority, 55.0)

    def _resource_component(self, available_resources: list[Any], action_name: str) -> float:
        if not available_resources:
            return 40.0
        if any(token in str(action_name).lower() for token in {"patrol", "dispatch", "escalate", "immediate"}):
            return min(100.0, 55.0 + len(available_resources) * 10.0)
        return min(100.0, 50.0 + len(available_resources) * 5.0)

    def _feasibility_component(self, action_name: str, available_resources: list[Any], operator_constraints: list[Any]) -> float:
        base = 70.0
        if any(token in str(action_name).lower() for token in {"patrol", "dispatch", "immediate", "escalate"}):
            base += 10.0
        if not available_resources:
            base -= 20.0
        if operator_constraints:
            base -= 8.0
        return self._clamp(base)

    def _risk_component(self, active_alerts: list[Any], operator_constraints: list[Any], action_name: str) -> float:
        base = 30.0
        if active_alerts:
            base += 25.0
        if operator_constraints:
            base += 10.0
        if any(token in str(action_name).lower() for token in {"monitor", "track"}):
            base -= 10.0
        return self._clamp(base)

    def _mission_alignment(self, action_name: str, mission_priority: str, response_recommendations: list[Any]) -> float:
        base = self._mission_component(mission_priority) * 0.6
        if response_recommendations:
            base += 10.0
        if any(token in str(action_name).lower() for token in {"dispatch", "escalate", "immediate"}):
            base += 10.0
        return self._clamp(base)

    def _category_for_name(self, action_name: str) -> str:
        text = str(action_name).lower()
        if any(token in text for token in {"dispatch", "patrol", "escalate", "immediate"}):
            return "response"
        if any(token in text for token in {"monitor", "track"}):
            return "monitor"
        return "support"

    def _priority_for_name(self, action_name: str) -> int:
        text = str(action_name).lower()
        if any(token in text for token in {"dispatch", "escalate", "immediate"}):
            return 100
        if any(token in text for token in {"monitor", "track"}):
            return 60
        return 70

    def _clamp(self, value: float) -> float:
        return max(0.0, min(100.0, value))
