"""Sprint 7 — Aircraft Components & Configuration tests."""

from __future__ import annotations

import uuid
from decimal import Decimal

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()


def _catalog_engine_id() -> str:
    items = client.get("/api/v1/components/catalog", params={"component_type": "engine"}).json()
    assert items
    return items[0]["id"]


def test_seeded_ata_and_catalog():
    login_as("operator")
    ata = client.get("/api/v1/components/ata-chapters")
    assert ata.status_code == 200
    chapters = {f"{i['chapter_number']}-{i['subchapter']}" for i in ata.json()}
    assert "71-00" in chapters
    assert "49-00" in chapters

    catalog = client.get("/api/v1/components/catalog")
    assert catalog.status_code == 200
    parts = {i["part_number"] for i in catalog.json()}
    assert "CFM56-5B4" in parts


def test_tenant_isolation_on_serialized_list():
    login_as("operator")
    denied = client.get("/api/v1/components/serialized", params={"organization_id": "org-aviation-west"})
    assert denied.status_code == 403


def test_viewer_rbac_read_only():
    login_as("viewer")
    assert client.get("/api/v1/components/serialized").status_code == 200
    assert client.get("/api/v1/components/aircraft/ac-c-gmea/configuration").status_code == 200
    denied = client.post(
        "/api/v1/components/serialized",
        json={"catalog_item_id": "x", "serial_number": "NOPE"},
    )
    assert denied.status_code == 403


def test_duplicate_serial_rejected():
    login_as("operator")
    catalog_id = _catalog_engine_id()
    suffix = uuid.uuid4().hex[:8].upper()
    payload = {"catalog_item_id": catalog_id, "serial_number": f"DUP-{suffix}", "component_status": "stores"}
    assert client.post("/api/v1/components/serialized", json=payload).status_code == 201
    again = client.post("/api/v1/components/serialized", json=payload)
    assert again.status_code == 409


def test_install_remove_transfer_and_history():
    login_as("operator")
    catalog_id = _catalog_engine_id()
    suffix = uuid.uuid4().hex[:8].upper()
    created = client.post(
        "/api/v1/components/serialized",
        json={
            "catalog_item_id": catalog_id,
            "serial_number": f"MOV-{suffix}",
            "component_status": "stores",
            "tsn_hours": "10.00",
            "csn_cycles": 5,
            "hour_limit": "1000.00",
            "cycle_limit": 500,
        },
    )
    assert created.status_code == 201, created.text
    component_id = created.json()["id"]

    installed = client.post(
        f"/api/v1/components/serialized/{component_id}/install",
        json={
            "aircraft_id": "ac-c-gmea",
            "position": f"ENG2-{suffix[:4]}",
            "aircraft_hours": "2000.00",
            "aircraft_cycles": 1000,
            "reason": "install_test",
            "reference": "WO-1",
        },
    )
    assert installed.status_code == 200, installed.text
    body = installed.json()
    assert body["component_status"] == "installed"
    assert body["current_aircraft_id"] == "ac-c-gmea"

    # Simultaneous install on same position blocked.
    other = client.post(
        "/api/v1/components/serialized",
        json={"catalog_item_id": catalog_id, "serial_number": f"OCC-{suffix}", "component_status": "stores"},
    ).json()["id"]
    conflict = client.post(
        f"/api/v1/components/serialized/{other}/install",
        json={
            "aircraft_id": "ac-c-gmea",
            "position": f"ENG2-{suffix[:4]}",
            "aircraft_hours": "2000.00",
            "aircraft_cycles": 1000,
        },
    )
    assert conflict.status_code == 409

    removed = client.post(
        f"/api/v1/components/serialized/{component_id}/remove",
        json={
            "destination_status": "maintenance",
            "aircraft_hours": "2100.50",
            "aircraft_cycles": 1040,
            "reason": "remove_test",
        },
    )
    assert removed.status_code == 200, removed.text
    removed_body = removed.json()
    assert removed_body["component_status"] == "maintenance"
    assert removed_body["current_aircraft_id"] is None
    # TSN 10 + (2100.50 - 2000) = 110.50
    assert Decimal(str(removed_body["tsn_hours"])) == Decimal("110.50")
    assert removed_body["csn_cycles"] == 45  # 5 + 40

    transferred = client.post(
        f"/api/v1/components/serialized/{component_id}/transfer",
        json={"to_status": "stores", "reason": "back_to_stores"},
    )
    assert transferred.status_code == 200
    assert transferred.json()["component_status"] == "stores"

    history = client.get(f"/api/v1/components/serialized/{component_id}/history")
    assert history.status_code == 200
    events = [h["event_type"] for h in history.json()]
    assert "install" in events
    assert "remove" in events
    assert "transfer" in events


def test_cannot_install_on_two_aircraft():
    login_as("operator")
    catalog_id = _catalog_engine_id()
    suffix = uuid.uuid4().hex[:8].upper()
    component_id = client.post(
        "/api/v1/components/serialized",
        json={"catalog_item_id": catalog_id, "serial_number": f"TWO-{suffix}", "component_status": "stores"},
    ).json()["id"]
    first = client.post(
        f"/api/v1/components/serialized/{component_id}/install",
        json={"aircraft_id": "ac-c-gmea", "position": f"P-{suffix[:4]}", "aircraft_hours": "100", "aircraft_cycles": 10},
    )
    assert first.status_code == 200
    second = client.post(
        f"/api/v1/components/serialized/{component_id}/install",
        json={"aircraft_id": "ac-c-gmeb", "position": f"Q-{suffix[:4]}", "aircraft_hours": "100", "aircraft_cycles": 10},
    )
    assert second.status_code == 409


def test_cannot_remove_before_install():
    login_as("operator")
    catalog_id = _catalog_engine_id()
    suffix = uuid.uuid4().hex[:8].upper()
    component_id = client.post(
        "/api/v1/components/serialized",
        json={"catalog_item_id": catalog_id, "serial_number": f"NRM-{suffix}", "component_status": "stores"},
    ).json()["id"]
    removed = client.post(
        f"/api/v1/components/serialized/{component_id}/remove",
        json={"destination_status": "stores", "aircraft_hours": "100", "aircraft_cycles": 10},
    )
    assert removed.status_code == 409
    assert "not installed" in removed.json()["detail"].lower()


def test_install_remove_each_use_single_commit():
    """Install and remove each flush+commit once (history + state in one transaction)."""
    from unittest.mock import patch

    from app.components.repository import ComponentRepository
    from app.components.schemas import InstallRequest, RemoveRequest
    from app.components.service import ComponentService
    from app.database import SessionLocal

    login_as("operator")
    catalog_id = _catalog_engine_id()
    suffix = uuid.uuid4().hex[:8].upper()
    component_id = client.post(
        "/api/v1/components/serialized",
        json={"catalog_item_id": catalog_id, "serial_number": f"TXN-{suffix}", "component_status": "stores"},
    ).json()["id"]

    db = SessionLocal()
    try:
        service = ComponentService(db)
        commits: list[str] = []
        real_commit = ComponentRepository.commit

        def tracking_commit(self):
            commits.append("commit")
            return real_commit(self)

        with patch.object(ComponentRepository, "commit", tracking_commit):
            service.install(
                component_id,
                InstallRequest(
                    aircraft_id="ac-c-gmea",
                    position=f"TXN-{suffix[:4]}",
                    aircraft_hours=Decimal("500.00"),
                    aircraft_cycles=50,
                ),
                username="operator",
                session_role="operator",
            )
            assert commits == ["commit"]

            service.remove(
                component_id,
                RemoveRequest(
                    destination_status="stores",
                    aircraft_hours=Decimal("520.00"),
                    aircraft_cycles=55,
                ),
                username="operator",
                session_role="operator",
            )
            assert commits == ["commit", "commit"]
    finally:
        db.close()


def test_transfer_remove_and_install_single_transaction():
    """Aircraft-to-aircraft transfer must commit once (remove+install, no race window)."""
    from unittest.mock import patch

    from app.components.repository import ComponentRepository
    from app.components.schemas import TransferRequest
    from app.components.service import ComponentService
    from app.database import SessionLocal

    login_as("operator")
    catalog_id = _catalog_engine_id()
    suffix = uuid.uuid4().hex[:8].upper()
    component_id = client.post(
        "/api/v1/components/serialized",
        json={"catalog_item_id": catalog_id, "serial_number": f"XFR-{suffix}", "component_status": "stores"},
    ).json()["id"]
    assert (
        client.post(
            f"/api/v1/components/serialized/{component_id}/install",
            json={
                "aircraft_id": "ac-c-gmea",
                "position": f"XA-{suffix[:4]}",
                "aircraft_hours": "300",
                "aircraft_cycles": 30,
            },
        ).status_code
        == 200
    )

    db = SessionLocal()
    try:
        service = ComponentService(db)
        commits: list[str] = []
        real_commit = ComponentRepository.commit

        def tracking_commit(self):
            commits.append("commit")
            return real_commit(self)

        with patch.object(ComponentRepository, "commit", tracking_commit):
            out = service.transfer(
                component_id,
                TransferRequest(
                    to_status="installed",
                    to_aircraft_id="ac-c-gmeb",
                    position=f"XB-{suffix[:4]}",
                    aircraft_hours=Decimal("310.00"),
                    aircraft_cycles=32,
                    reason="atomic_transfer",
                ),
                username="operator",
                session_role="operator",
            )
        assert commits == ["commit"]
        assert out.component_status == "installed"
        assert out.current_aircraft_id == "ac-c-gmeb"
        assert out.installation_position == f"XB-{suffix[:4]}"
    finally:
        db.close()

    history = client.get("/api/v1/components/history", params={"component_id": component_id})
    assert history.status_code == 200
    events = [h["event_type"] for h in history.json()]
    assert events.count("install") >= 2
    assert "remove" in events


def test_life_limits_and_time_cycle_updates():
    login_as("operator")
    catalog_id = _catalog_engine_id()
    suffix = uuid.uuid4().hex[:8].upper()
    component_id = client.post(
        "/api/v1/components/serialized",
        json={
            "catalog_item_id": catalog_id,
            "serial_number": f"LL-{suffix}",
            "component_status": "stores",
            "tsn_hours": "100.00",
            "csn_cycles": 20,
        },
    ).json()["id"]

    life = client.patch(
        f"/api/v1/components/serialized/{component_id}/life-limits",
        json={"hour_limit": "500.00", "cycle_limit": 200},
    )
    assert life.status_code == 200
    assert Decimal(str(life.json()["remaining_hours"])) == Decimal("400.00")
    assert life.json()["remaining_cycles"] == 180

    cycles = client.patch(
        f"/api/v1/components/serialized/{component_id}/time-cycles",
        json={"tsn_hours": "150.25", "csn_cycles": 30},
    )
    assert cycles.status_code == 200
    assert Decimal(str(cycles.json()["tsn_hours"])) == Decimal("150.25")
    assert Decimal(str(cycles.json()["remaining_hours"])) == Decimal("349.75")


def test_aircraft_configuration_endpoint():
    login_as("operator")
    config = client.get("/api/v1/components/aircraft/ac-c-gmea/configuration")
    assert config.status_code == 200
    body = config.json()
    assert body["aircraft_id"] == "ac-c-gmea"
    assert body["organization_id"] == "org-aviation-east"
    assert isinstance(body["installed"], list)
    assert any(item["serial_number"] == "ENG-SN-1001" for item in body["installed"])


def test_catalog_create_requires_admin_and_audits_mutations():
    login_as("operator")
    denied = client.post(
        "/api/v1/components/ata-chapters",
        json={"chapter_number": "24", "subchapter": "00", "title": "Electrical Power"},
    )
    assert denied.status_code == 403

    login_as("admin")
    suffix = uuid.uuid4().hex[:4]
    created = client.post(
        "/api/v1/components/ata-chapters",
        json={"chapter_number": f"9{suffix[:1]}", "subchapter": "00", "title": f"Chapter {suffix}"},
    )
    assert created.status_code == 201

    login_as("admin")
    events = client.get("/admin/audit", params={"action": "component.ata.create", "limit": 20})
    assert events.status_code == 200
    assert any(item["action"] == "component.ata.create" for item in events.json())
