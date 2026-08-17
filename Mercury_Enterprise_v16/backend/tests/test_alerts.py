import asyncio

from app.alerts import AlertManager
from app.core.event_bus import EventBus


def test_create_and_list_alerts():
    manager = AlertManager(max_history=3)
    alert = manager.create_alert(
        incident_id="inc-1",
        severity="high",
        title="Threat detected",
        message="Threat detected by radar",
        source="sensor",
    )

    assert alert.incident_id == "inc-1"
    assert manager.get_alerts(incident_id="inc-1")[0].id == alert.id


def test_event_subscription():
    bus = EventBus()
    manager = AlertManager(event_bus_instance=bus, max_history=5)

    asyncio.run(bus.publish("ai.alert", {"message": "AI threat alert"}, source="ai"))

    alerts = manager.get_alerts()
    assert len(alerts) == 1
    assert alerts[0].title == "AI alert"
    assert alerts[0].source == "ai"


def test_acknowledge_and_export():
    manager = AlertManager(max_history=5)
    alert = manager.create_alert("inc-2", "medium", "Status change", "Incident updated")

    manager.acknowledge(alert.id)
    assert manager.get_alerts(incident_id="inc-2")[0].acknowledged is True

    exported = manager.export_json()
    assert exported[0]["acknowledged"] is True


def test_alerts_are_tenant_filtered():
    manager = AlertManager(max_history=10)
    east = manager.create_alert(
        "inc-east",
        "high",
        "East alert",
        "east only",
        organization_id="org-aviation-east",
        site_id="site-cyul",
    )
    west = manager.create_alert(
        "inc-west",
        "critical",
        "West alert",
        "west only",
        organization_id="org-aviation-west",
        site_id="site-cyvr",
    )
    platform = manager.create_alert(None, "info", "System started", "platform")

    east_visible = manager.get_alerts(organization_id="org-aviation-east", site_id="site-cyul")
    east_ids = {item.id for item in east_visible}
    assert east.id in east_ids
    assert platform.id in east_ids
    assert west.id not in east_ids

    assert manager.get_alert(west.id, organization_id="org-aviation-east") is None
    assert manager.acknowledge(west.id, organization_id="org-aviation-east") is None
    assert manager.acknowledge(west.id, organization_id="org-aviation-west", site_id="site-cyvr") is not None
