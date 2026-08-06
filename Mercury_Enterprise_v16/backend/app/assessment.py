def generate_assessment(incident):
    """Generate a deterministic decision-support assessment for the MVP.

    This is a rules-based demonstration, not a certified safety or security decision system.
    """
    severity = str(incident.severity or "low").lower()

    scores = {
        "critical": (97, "CRITICAL"),
        "high": (92, "HIGH"),
        "medium": (74, "MEDIUM"),
        "low": (46, "LOW"),
    }
    score, level = scores.get(severity, (40, "LOW"))

    return {
        "score": score,
        "level": level,
        "reasoning": [
            "Object entered monitored airspace.",
            "Sensor observations were correlated by Mercury.",
            "The object remained inside the protected area.",
            "Confidence exceeded the operational review threshold.",
        ],
        "recommendations": [
            "Notify Airport Operations",
            "Dispatch Security Patrol",
            "Continue RF and visual monitoring",
            "Record the incident for investigation",
        ],
    }
