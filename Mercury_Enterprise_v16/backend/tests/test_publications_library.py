"""Sprint 7 extension — Publications & Technical Library tests."""

from __future__ import annotations

import uuid

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()


def test_seeded_publication_types_and_library():
    login_as("operator")
    types = client.get("/api/v1/publications/types")
    assert types.status_code == 200
    codes = {t["code"] for t in types.json()}
    assert "AMM" in codes
    assert "AIPC" in codes
    assert "CMM" in codes
    assert "SB" in codes
    assert "DDG-FAA" in codes

    browse = client.get("/api/v1/library/browse")
    assert browse.status_code == 200
    assert browse.json()["path"][0] == "library"
    assert any(n["node_type"] == "manufacturer" for n in browse.json()["nodes"])


def test_tenant_isolation_on_publications():
    login_as("operator")
    denied = client.get("/api/v1/publications", params={"organization_id": "org-aviation-west"})
    assert denied.status_code == 403


def test_viewer_rbac_read_only():
    login_as("viewer")
    assert client.get("/api/v1/publications/types").status_code == 200
    assert client.get("/api/v1/library/search", params={"q": "A320"}).status_code == 200
    denied = client.post(
        "/api/v1/publications",
        json={
            "publication_type_code": "AMM",
            "title": "Nope",
            "publication_number": "NOPE-1",
        },
    )
    assert denied.status_code == 403


def test_operator_cannot_archive_or_change_access():
    login_as("operator")
    pubs = client.get("/api/v1/publications", params={"publication_code": "AMM"}).json()
    assert pubs
    pub_id = pubs[0]["id"]
    assert client.post(f"/api/v1/publications/{pub_id}/archive").status_code == 403
    assert (
        client.post(
            f"/api/v1/publications/{pub_id}/access-classification",
            json={"access_classification": "restricted"},
        ).status_code
        == 403
    )


def test_revision_history_and_duplicate_prevention():
    login_as("operator")
    suffix = uuid.uuid4().hex[:8].upper()
    created = client.post(
        "/api/v1/publications",
        json={
            "publication_type_code": "SB",
            "title": f"SB Test {suffix}",
            "publication_number": f"SB-{suffix}",
            "manufacturer_id": "mfr-airbus",
            "aircraft_model_id": "model-a320",
            "ata_chapter_id": "ata-71-00",
            "revision_number": "Rev 01",
            "activate_revision": True,
            "storage": {"kind": "external_url", "uri": "https://example.invalid/sb/rev01"},
            "access_classification": "internal",
        },
    )
    assert created.status_code == 201, created.text
    pub_id = created.json()["id"]
    assert created.json()["current_revision_number"] == "Rev 01"

    draft = client.post(
        f"/api/v1/publications/{pub_id}/revisions",
        json={
            "revision_number": "Rev 02",
            "activate": False,
            "storage": {"kind": "external_url", "uri": "https://example.invalid/sb/rev02"},
            "change_summary": "Second revision draft",
        },
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["status"] == "draft"
    rev2_id = draft.json()["id"]

    dup = client.post(
        f"/api/v1/publications/{pub_id}/revisions",
        json={"revision_number": "Rev 02", "storage": {"kind": "none"}},
    )
    assert dup.status_code == 409

    history = client.get(f"/api/v1/publications/{pub_id}/revisions")
    assert history.status_code == 200
    assert len(history.json()) == 2

    login_as("admin")
    activated = client.post(f"/api/v1/publications/{pub_id}/revisions/{rev2_id}/activate")
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "current"

    history = client.get(f"/api/v1/publications/{pub_id}/revisions").json()
    statuses = {h["revision_number"]: h["status"] for h in history}
    assert statuses["Rev 01"] == "superseded"
    assert statuses["Rev 02"] == "current"

    pub = client.get(f"/api/v1/publications/{pub_id}").json()
    assert pub["current_revision_id"] == rev2_id
    assert pub["current_revision_number"] == "Rev 02"


def test_ata_and_model_and_component_linkage():
    login_as("operator")
    by_ata = client.get("/api/v1/publications/by-ata/ata-71-00")
    assert by_ata.status_code == 200
    assert any(p["publication_code"] in {"AMM", "AIPC"} for p in by_ata.json())

    by_model = client.get("/api/v1/publications/by-model/model-a320")
    assert by_model.status_code == 200
    assert len(by_model.json()) >= 1

    components = client.get("/api/v1/components/serialized").json()
    engine = next(c for c in components if c["serial_number"] == "ENG-SN-1001")
    related = client.get(f"/api/v1/publications/by-component/{engine['id']}")
    assert related.status_code == 200
    body = related.json()
    assert body["serial_number"] == "ENG-SN-1001"
    assert any(p["publication_code"] == "CMM" for p in body["publications"]) or any(
        p["publication_code"] in {"AMM", "AIPC", "CMM"} for p in body["publications"]
    )

    by_aircraft = client.get("/api/v1/publications/by-aircraft/ac-c-gmea")
    assert by_aircraft.status_code == 200
    assert len(by_aircraft.json()) >= 1


def test_search_and_library_navigation():
    login_as("operator")
    search = client.get("/api/v1/library/search", params={"q": "CFM56", "publication_code": "CMM"})
    assert search.status_code == 200
    assert any("CFM56" in p["title"] for p in search.json())

    filtered = client.get(
        "/api/v1/publications",
        params={"aircraft_model_id": "model-a320", "revision": "Rev 12"},
    )
    assert filtered.status_code == 200
    assert any(p["publication_number"] == "CMM-CFM56-5B" for p in filtered.json())

    step1 = client.get("/api/v1/library/browse").json()
    mfr = next(n for n in step1["nodes"] if n["id"] == "mfr-airbus")
    step2 = client.get("/api/v1/library/browse", params={"manufacturer_id": mfr["id"]}).json()
    assert any(n["node_type"] == "aircraft_family" for n in step2["nodes"])
    family = next(n for n in step2["nodes"] if n["node_type"] == "aircraft_family")
    step2b = client.get(
        "/api/v1/library/browse",
        params={"manufacturer_id": "mfr-airbus", "family_id": family["id"]},
    ).json()
    assert any(n["node_type"] == "aircraft_model" for n in step2b["nodes"])
    step3 = client.get(
        "/api/v1/library/browse",
        params={"manufacturer_id": "mfr-airbus", "aircraft_model_id": "model-a320"},
    ).json()
    assert any(n["node_type"] == "publication_type" for n in step3["nodes"])
    step4 = client.get(
        "/api/v1/library/browse",
        params={
            "manufacturer_id": "mfr-airbus",
            "aircraft_model_id": "model-a320",
            "publication_code": "AMM",
        },
    ).json()
    assert any(n["node_type"] in {"ata_chapter", "publication"} for n in step4["nodes"])


def test_admin_access_control_archive_and_audit():
    login_as("operator")
    suffix = uuid.uuid4().hex[:8].upper()
    created = client.post(
        "/api/v1/publications",
        json={
            "publication_type_code": "AW",
            "title": f"Advisory {suffix}",
            "publication_number": f"AW-{suffix}",
            "revision_number": "A",
            "activate_revision": True,
            "storage": {"kind": "none"},
        },
    )
    assert created.status_code == 201, created.text
    pub_id = created.json()["id"]

    login_as("admin")
    access = client.post(
        f"/api/v1/publications/{pub_id}/access-classification",
        json={"access_classification": "restricted"},
    )
    assert access.status_code == 200
    assert access.json()["access_classification"] == "restricted"

    archived = client.post(f"/api/v1/publications/{pub_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    events = client.get("/admin/audit", params={"action": "publication.create", "limit": 50})
    assert events.status_code == 200
    assert any(item["action"] == "publication.create" for item in events.json())

    events = client.get("/admin/audit", params={"action": "publication.access_control", "limit": 50})
    assert any(item["action"] == "publication.access_control" for item in events.json())

    events = client.get("/admin/audit", params={"action": "publication.archive", "limit": 50})
    assert any(item["action"] == "publication.archive" for item in events.json())


def test_metadata_update_audited():
    login_as("operator")
    pubs = client.get("/api/v1/publications", params={"publication_code": "AIPC"}).json()
    pub_id = pubs[0]["id"]
    updated = client.patch(
        f"/api/v1/publications/{pub_id}",
        json={"description": "Updated AIPC metadata for audit check"},
    )
    assert updated.status_code == 200
    login_as("admin")
    events = client.get("/admin/audit", params={"action": "publication.update", "limit": 50})
    assert any(item["action"] == "publication.update" for item in events.json())
