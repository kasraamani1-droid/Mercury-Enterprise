from __future__ import annotations

from typing import Any

from .classifier import ThreatClassifier
from .confidence import ConfidenceScorer
from .models import ThreatAssessmentResult, ThreatLevel
from .recommendations import RecommendationEngine


class ThreatRiskEngine:
    """Compose a modular backend threat assessment result."""

    def __init__(self) -> None:
        self._confidence_scorer = ConfidenceScorer()
        self._classifier = ThreatClassifier()
        self._recommendation_engine = RecommendationEngine()

    def assess(self, signal_strength: float, corroboration: float) -> ThreatAssessmentResult:
        confidence = self._confidence_scorer.score(signal_strength, corroboration)
        score = self._calculate_score(signal_strength, corroboration)
        level = self._classifier.classify(score)
        recommendations = self._recommendation_engine.generate(level)
        return ThreatAssessmentResult(
            score=score,
            confidence=confidence,
            level=level,
            recommendations=recommendations,
        )

    def _calculate_score(self, signal_strength: float, corroboration: float) -> int:
        raw_score = (signal_strength * 0.7) + (corroboration * 0.3)
        score = int(round(raw_score))
        return max(0, min(100, score))

    def evaluate(self, signal_strength: float, corroboration: float) -> dict[str, Any]:
        result = self.assess(signal_strength, corroboration)
        return result.to_dict()
