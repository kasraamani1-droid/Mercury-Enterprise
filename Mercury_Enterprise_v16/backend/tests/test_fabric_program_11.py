"""Program 11 — Universal Data Fabric tests."""

from __future__ import annotations

import uuid

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    r = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert r.status_code == 200
    return r.json()


def test_fabric_seed_overview_and_catalog():
    login_as("operator")
    overview = client.get("/api/v1/fabric/overview")
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["entity_types"] >= 30
    assert body["passports"] >= 1
    assert body["retention_policies"] >= 1
    types = client.get("/api/v1/fabric/entity-types")
    assert types.status_code == 200
    codes = {t["code"] for t in types.json()}
    assert "aircraft" in codes
    assert "work_order" in codes
    assert "marketplace_listing" in codes
    assert "authority_audit" in codes


def test_viewer_can_read_not_manage():
    login_as("viewer")
    assert client.get("/api/v1/fabric/overview").status_code == 200
    assert (
        client.post(
            "/api/v1/fabric/passports",
            json={"entity_type": "aircraft", "entity_id": "x", "display_name": "Nope"},
        ).status_code
        == 403
    )


def test_passport_relationship_event_thread():
    login_as("operator")
    suffix = uuid.uuid4().hex[:8]
    aircraft = client.post(
        "/api/v1/fabric/passports",
        json={
            "entity_type": "aircraft",
            "entity_id": f"ac-test-{suffix}",
            "display_name": f"Test Aircraft {suffix}",
            "tags_json": '["test","aircraft"]',
        },
    )
    assert aircraft.status_code == 201, aircraft.text
    ac_id = aircraft.json()["id"]
    assert aircraft.json()["passport_number"].startswith("PP-")
    assert aircraft.json()["digital_identity"].startswith("did:mercury:")

    component = client.post(
        "/api/v1/fabric/passports",
        json={
            "entity_type": "component",
            "entity_id": f"comp-test-{suffix}",
            "display_name": f"Test Component {suffix}",
        },
    )
    assert component.status_code == 201, component.text
    comp_id = component.json()["id"]

    rel = client.post(
        "/api/v1/fabric/relationships",
        json={
            "from_passport_id": comp_id,
            "to_passport_id": ac_id,
            "relationship_type": "installed_on",
            "cardinality": "many_to_many",
        },
    )
    assert rel.status_code == 201, rel.text

    event = client.post(
        "/api/v1/fabric/events",
        json={
            "passport_id": comp_id,
            "entity_type": "component",
            "entity_id": f"comp-test-{suffix}",
            "event_type": "installed",
            "title": "Component installed on aircraft",
        },
    )
    assert event.status_code == 201, event.text

    thread = client.get(f"/api/v1/fabric/passports/{ac_id}/thread", params={"max_depth": 3})
    assert thread.status_code == 200, thread.text
    tbody = thread.json()
    assert tbody["root_passport_id"] == ac_id
    assert len(tbody["nodes"]) >= 2
    assert len(tbody["edges"]) >= 1

    hist = client.get(f"/api/v1/fabric/passports/{ac_id}/history")
    assert hist.status_code == 200
    assert len(hist.json()) >= 1


def test_fabric_search_and_tags():
    login_as("operator")
    suffix = uuid.uuid4().hex[:6]
    pp = client.post(
        "/api/v1/fabric/passports",
        json={
            "entity_type": "tool",
            "entity_id": f"tool-{suffix}",
            "display_name": f"Torque Searchable {suffix}",
        },
    ).json()
    tag = client.post(
        "/api/v1/fabric/tags",
        json={"passport_id": pp["id"], "tag": "calibration", "category": "tooling"},
    )
    assert tag.status_code == 201, tag.text
    hits = client.get("/api/v1/fabric/search", params={"q": f"Torque Searchable {suffix}"})
    assert hits.status_code == 200
    assert hits.json()
    assert any(h["passport"]["id"] == pp["id"] for h in hits.json())


def test_legal_hold_blocks_archive():
    login_as("operator")
    suffix = uuid.uuid4().hex[:6]
    pp = client.post(
        "/api/v1/fabric/passports",
        json={"entity_type": "publication", "entity_id": f"pub-{suffix}", "display_name": "Hold Me"},
    ).json()
    hold = client.post(
        "/api/v1/fabric/governance/legal-holds",
        json={"passport_id": pp["id"], "reason": "litigation hold test"},
    )
    assert hold.status_code == 201, hold.text
    blocked = client.post(
        f"/api/v1/fabric/passports/{pp['id']}/lifecycle",
        params={"lifecycle": "archived"},
    )
    assert blocked.status_code == 409
    released = client.post(f"/api/v1/fabric/governance/legal-holds/{hold.json()['id']}/release")
    assert released.status_code == 200
    ok = client.post(
        f"/api/v1/fabric/passports/{pp['id']}/lifecycle",
        params={"lifecycle": "archived"},
    )
    assert ok.status_code == 200
    assert ok.json()["lifecycle"] == "archived"


def test_tenant_isolation_fabric():
    login_as("operator")
    assert (
        client.get("/api/v1/fabric/passports", params={"organization_id": "org-aviation-west"}).status_code
        == 403
    )
