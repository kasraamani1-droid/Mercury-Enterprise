from __future__ import annotations


class ConfidenceScorer:
    """Calculate a confidence percentage from the strength of observed signals."""

    def score(self, signal_strength: float, corroboration: float) -> int:
        raw_score = (signal_strength * 0.6) + (corroboration * 0.4)
        return max(0, min(100, int(round(raw_score))))
