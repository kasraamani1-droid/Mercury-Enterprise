import asyncio
from datetime import datetime, timezone

from app.core.event_bus import EventBus
from app.timeline import TimelineManager


def test_adding_events():
    manager = TimelineManager(max_history=3)

    entry = manager.add_event(
        event_type="mission.started",
        severity="high",
        source="test",
        message="Mission started",
        metadata={"phase": "bootstrap"},
    )

    assert entry.event_type == "mission.started"
    assert manager.last() is entry
    assert manager.get_events(limit=1)[0].id == entry.id


def test_event_subscription():
    bus = EventBus()
    manager = TimelineManager(event_bus_instance=bus, max_history=5)

    asyncio.run(bus.publish("mission.completed", {"status": "done"}, source="sim"))

    entries = manager.get_events(event_type="mission.completed")
    assert len(entries) == 1
    assert entries[0].message == "Mission completed"
    assert entries[0].source == "sim"


def test_ordering_and_json_export():
    manager = TimelineManager(max_history=5)

    manager.add_event(
        event_type="alpha",
        message="First event",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    manager.add_event(
        event_type="beta",
        message="Second event",
        timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    ordered = manager.get_events(sort_desc=True)
    assert [entry.event_type for entry in ordered] == ["beta", "alpha"]

    exported = manager.export_json()
    assert exported[0]["event_type"] == "beta"
    assert exported[0]["message"] == "Second event"
