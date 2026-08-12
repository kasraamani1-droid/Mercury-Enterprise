from app.ai import ThreatRiskEngine, ThreatLevel


def test_assessment_output_shape():
    engine = ThreatRiskEngine()
    result = engine.assess(82, 76)

    assert result.score <= 100
    assert result.confidence <= 100
    assert result.level in {
        ThreatLevel.LOW,
        ThreatLevel.MEDIUM,
        ThreatLevel.HIGH,
        ThreatLevel.CRITICAL,
    }
    assert isinstance(result.recommendations, list)


def test_evaluate_returns_mapping():
    engine = ThreatRiskEngine()
    payload = engine.evaluate(20, 10)

    assert payload["score"] == 17
    assert payload["confidence"] == 16
    assert payload["level"] == "LOW"
    assert payload["recommendations"] == ["Continue monitoring"]
