from __future__ import annotations

from typing import Any


class DecisionExplanationEngine:
    """Build human-readable decision explanations and structured review factors."""

    def explain(
        self,
        context: dict[str, Any],
        ranked_actions: list[dict[str, Any]],
        selected: dict[str, Any],
    ) -> dict[str, Any]:
        warnings: list[str] = []
        assumptions: list[str] = []
        uncertainty: list[str] = []
        factor_breakdown: list[dict[str, Any]] = []
        evidence_links: list[dict[str, str]] = []

        threat_level = str(context.get("threat_level") or "low").lower()
        threat_score = float(context.get("threat_score") or 0.0)
        fused_confidence = float(context.get("fused_confidence") or context.get("threat_confidence") or 0.0)

        assumptions.append("Recommendations are advisory and require explicit human review.")
        assumptions.append("Scoring uses deterministic weighted factors from the DecisionScoringEngine.")
        if context.get("mission_id"):
            assumptions.append(f"Mission context {context.get('mission_id')} was available for ranking.")
        else:
            warnings.append("Mission context was unavailable; the decision used only the supplied threat inputs.")
            assumptions.append("Mission context was not resolved; ranking used supplied threat inputs only.")

        if threat_level in {"high", "critical"}:
            factor_breakdown.append(
                {
                    "name": "threat_level",
                    "weight_or_score": threat_score,
                    "detail": f"Elevated threat level ({threat_level}) increased urgency.",
                }
            )
        else:
            factor_breakdown.append(
                {
                    "name": "threat_level",
                    "weight_or_score": threat_score,
                    "detail": f"Threat level treated as {threat_level}.",
                }
            )

        if context.get("active_alerts"):
            factor_breakdown.append(
                {
                    "name": "active_alerts",
                    "weight_or_score": float(len(context.get("active_alerts") or [])),
                    "detail": "Active alerts increased urgency.",
                }
            )

        if context.get("operator_constraints"):
            constraints = [str(item) for item in (context.get("operator_constraints") or [])]
            factor_breakdown.append(
                {
                    "name": "operator_constraints",
                    "weight_or_score": float(len(constraints)),
                    "detail": "Operator constraints were considered when ranking the options.",
                }
            )
            for constraint in constraints:
                factor_breakdown.append(
                    {
                        "name": "constraint_effect",
                        "weight_or_score": 0.0,
                        "detail": f"Constraint effect: {constraint}",
                    }
                )

        if selected.get("reasons"):
            for reason in selected.get("reasons") or []:
                factor_breakdown.append(
                    {
                        "name": "selected_reason",
                        "weight_or_score": float(selected.get("overall_score") or 0.0),
                        "detail": str(reason),
                    }
                )

        if selected.get("constraints"):
            for constraint in selected.get("constraints") or []:
                factor_breakdown.append(
                    {
                        "name": "selected_constraint",
                        "weight_or_score": 0.0,
                        "detail": str(constraint),
                    }
                )

        if fused_confidence and fused_confidence < 60:
            uncertainty.append(f"Fused confidence is moderate/low ({fused_confidence:.0f}); treat ranking as provisional.")
        if len(ranked_actions) < 2:
            uncertainty.append("Few ranked alternatives were available; comparison confidence is limited.")
        elif ranked_actions:
            top = float(ranked_actions[0].get("overall_score") or 0.0)
            second = float(ranked_actions[1].get("overall_score") or 0.0) if len(ranked_actions) > 1 else 0.0
            if abs(top - second) < 5:
                uncertainty.append("Top alternatives scored closely; human judgment should resolve near-ties.")

        if context.get("mission_id"):
            evidence_links.append({"label": "mission", "ref": str(context.get("mission_id"))})
        if context.get("track_id"):
            evidence_links.append({"label": "track", "ref": str(context.get("track_id"))})
        for alert in (context.get("active_alerts") or [])[:5]:
            if isinstance(alert, dict):
                ref = str(alert.get("id") or alert.get("title") or "alert")
                evidence_links.append({"label": "alert", "ref": ref})

        selected_name = selected.get("name", "recommended action")
        selected_score = float(selected.get("overall_score") or 0.0)
        competitor_score = float(ranked_actions[1].get("overall_score") or 0.0) if len(ranked_actions) > 1 else 0.0
        reasoning = (
            f"The engine selected {selected_name} because it achieved the highest deterministic score "
            f"({selected_score:.0f}) among the candidate actions"
            + (f", ahead of the next option ({competitor_score:.0f})" if len(ranked_actions) > 1 else "")
            + "."
        )

        return {
            "reasoning": reasoning,
            "warnings": warnings,
            "assumptions": assumptions,
            "uncertainty": uncertainty,
            "factor_breakdown": factor_breakdown,
            "evidence_links": evidence_links,
        }
