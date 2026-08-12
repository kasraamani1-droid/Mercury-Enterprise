from datetime import datetime, timezone

from app.fusion import FusionEngine, Observation, SensorType, TrackStatus


def test_ingest_observation_creates_track():
    engine = FusionEngine(correlation_threshold=0.4)
    observation = Observation(
        source="radar",
        sensor_type=SensorType.RADAR,
        target_id="target-1",
        timestamp=datetime.now(timezone.utc),
        latitude=10.0,
        longitude=20.0,
        altitude=100.0,
        speed=50.0,
        heading=180.0,
        confidence=70.0,
        classification="drone",
    )

    track = engine.ingest_observation(observation)

    assert track.target_id == "target-1"
    assert track.status == TrackStatus.ACTIVE
    assert track.observation_count == 1


def test_correlate_observation_returns_score():
    engine = FusionEngine(correlation_threshold=0.4)
    observation_a = Observation(
        source="radar",
        sensor_type=SensorType.RADAR,
        target_id="target-2",
        timestamp=datetime.now(timezone.utc),
        latitude=10.0,
        longitude=20.0,
        altitude=100.0,
        speed=50.0,
        heading=180.0,
        confidence=70.0,
        classification="drone",
    )
    engine.ingest_observation(observation_a)

    observation_b = Observation(
        source="camera",
        sensor_type=SensorType.CAMERA,
        target_id="target-2",
        timestamp=datetime.now(timezone.utc),
        latitude=10.2,
        longitude=20.1,
        altitude=102.0,
        speed=48.0,
        heading=182.0,
        confidence=80.0,
        classification="drone",
    )

    score, track = engine.correlate_observation(observation_b)
    assert score >= 0.0
    assert track is not None


def test_clear_removes_tracks():
    engine = FusionEngine(correlation_threshold=0.4)
    observation = Observation(
        source="simulation",
        sensor_type=SensorType.SIMULATION,
        target_id="target-3",
        timestamp=datetime.now(timezone.utc),
        latitude=1.0,
        longitude=2.0,
        altitude=50.0,
        speed=20.0,
        heading=90.0,
        confidence=60.0,
        classification="aircraft",
    )
    engine.ingest_observation(observation)
    engine.clear()
    assert engine.get_tracks() == []
