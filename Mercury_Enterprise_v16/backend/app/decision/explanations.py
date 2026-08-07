from __future__ import annotations

from typing import Any


class DecisionExplanationEngine:
    """Build human-readable decision explanations and warnings."""

    def explain(self, context: dict[str, Any], ranked_actions: list[dict[str, Any]], selected: dict[str, Any]) -> tuple[str, list[str]]:
        reasons = []
        warnings = []

        threat_level = str(context.get("threat_level") or "low").lower()
        if threat_level in {"high", "critical"}:
            reasons.append(f"The threat level was {threat_level}.")
        if context.get("active_alerts"):
            reasons.append("Active alerts increased urgency.")
        if context.get("operator_constraints"):
            reasons.append("Operator constraints were considered when ranking the options.")

        if not context.get("mission_id"):
            warnings.append("Mission context was unavailable; the decision used only the supplied threat inputs.")

        selected_name = selected.get("name", "recommended action")
        top_score = ranked_actions[0].get("overall_score", 0.0) if ranked_actions else 0.0
        selected_score = selected.get("overall_score", 0.0)
        reasoning = (
            f"The engine selected {selected_name} because it achieved the highest deterministic score "
            f"({selected_score:.0f}) among the candidate actions, exceeding the top competing option "
            f"({top_score:.0f})."
        )
        return reasoning, warnings + reasons
