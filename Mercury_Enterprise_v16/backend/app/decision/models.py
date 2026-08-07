from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class DecisionCandidate:
    action_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    category: str = "monitor"
    description: str = ""
    source_module: str = "decision_engine"
    priority: int = 0
    confidence: float = 0.0
    feasibility_score: float = 0.0
    risk_score: float = 0.0
    mission_alignment_score: float = 0.0
    resource_impact_score: float = 0.0
    overall_score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "source_module": self.source_module,
            "priority": self.priority,
            "confidence": round(self.confidence, 2),
            "feasibility_score": round(self.feasibility_score, 2),
            "risk_score": round(self.risk_score, 2),
            "mission_alignment_score": round(self.mission_alignment_score, 2),
            "resource_impact_score": round(self.resource_impact_score, 2),
            "overall_score": round(self.overall_score, 2),
            "reasons": self.reasons,
            "constraints": self.constraints,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class DecisionResult:
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    mission_id: str | None = None
    track_id: str | None = None
    context_summary: str = ""
    ranked_actions: list[DecisionCandidate] = field(default_factory=list)
    selected_recommendation: DecisionCandidate | None = None
    confidence: float = 0.0
    reasoning: str = ""
    warnings: list[str] = field(default_factory=list)
    requires_human_approval: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "created_at": self.created_at.isoformat(),
            "mission_id": self.mission_id,
            "track_id": self.track_id,
            "context_summary": self.context_summary,
            "ranked_actions": [action.to_dict() for action in self.ranked_actions],
            "selected_recommendation": self.selected_recommendation.to_dict() if self.selected_recommendation else None,
            "confidence": round(self.confidence, 2),
            "reasoning": self.reasoning,
            "warnings": self.warnings,
            "requires_human_approval": self.requires_human_approval,
            "metadata": self.metadata,
        }
