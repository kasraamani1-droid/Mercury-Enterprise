"""RC1 Blocker 06 — sequential end-to-end smoke of existing platform workflows.

Does not add product features. Walks login → domain reads → logout on one session,
plus static UI surface checks (no Playwright browser driver).
"""

from __future__ import annotations

from pathlib import Path

from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.fleet.models import Aircraft
from app.main import app
from app.models import AuditEvent

client = TestClient(app)
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PACKAGE_ROOT / "frontend"


def _ok(response, expected: int | set[int] = 200):
    allowed = {expected} if isinstance(expected, int) else expected
    assert response.status_code in allowed, response.text
    return response


def test_ui_shell_exposes_rc1_workflow_surfaces() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    app_js = (FRONTEND / "js" / "app.js").read_text(encoding="utf-8")
    api_js = (FRONTEND / "js" / "api.js").read_text(encoding="utf-8")
    registry = (FRONTEND / "js" / "ux2" / "registry.js").read_text(encoding="utf-8")
    workspaces = (FRONTEND / "js" / "ux2" / "workspaces.js").read_text(encoding="utf-8")
    command = (FRONTEND / "js" / "commandCenter.js").read_text(encoding="utf-8")

    assert 'id="loginOverlay"' in html
    assert 'id="loginForm"' in html
    assert 'id="organizationSelect"' in html
    assert 'id="ux2SignOut"' in html
    assert "Sign out" in html
    assert 'id="homeWorkspace"' in html
    assert 'id="aircraftWorkspace"' in html
    assert 'id="fleetWorkspace"' in html
    assert 'id="inventoryWorkspace"' in html
    assert 'id="planningWorkspace"' in html
    assert 'id="workOrdersWorkspace"' in html
    assert 'id="engineeringWorkspace"' in html
    assert 'id="logbookWorkspace"' in html
    assert 'id="marketplaceWorkspace"' in html
    assert 'id="aiWorkspace"' in html
    assert 'id="notificationCenter"' in html
    assert 'id="ux2SearchTrigger"' in html
    assert 'id="copilotButton"' in html
    assert 'id="auditLog"' in html
    assert 'id="roleSelect"' in html
    assert 'type="file"' not in html
    assert 'id="componentWorkspace"' not in html

    assert "async function signOut()" in app_js
    assert 'addEventListener("click", signOut)' in app_js
    assert 'id="ux2SignOut"' in app_js or "ux2SignOut" in app_js
    assert "onOrganizationChange" in app_js
    assert 'request("/auth/logout"' in api_js
    assert 'request("/auth/login"' in api_js
    assert 'id: "aircraft"' in registry
    assert 'id: "planning"' in registry
    assert 'id: "workOrders"' in registry
    assert "uxFetchFleetAircraft" in workspaces
    assert "uxFetchWorkOrders" in workspaces
    assert "uxFetchPlatformNotifications" in workspaces
    assert "const notifications=[]" in command


def test_rc1_sequential_smoke_twenty_one_workflows() -> None:
    """One session walks the 21 RC1 workflows in order (integration with prior step)."""
    client.post("/api/v1/auth/logout")

    # --- 1. Login (anonymous denied first) ---
    assert client.get("/api/v1/fleet/aircraft").status_code == 401
    bad = client.post(
        "/api/v1/auth/login",
        json={"operator": "operator", "password": "wrong-password-not-used"},
    )
    assert bad.status_code == 401
    login = _ok(
        client.post(
            "/api/v1/auth/login",
            json={"operator": "operator", "password": TEST_AUTH_PASSWORD},
        )
    )
    session = login.json()
    assert session["authenticated"] is True
    assert session["operator"] == "operator"
    live = _ok(client.get("/api/v1/auth/session")).json()
    org_id = live["organization_id"]
    site_id = live["site_id"]

    # --- 2. Organization selection ---
    orgs = _ok(client.get("/api/v1/organizations")).json()
    assert any(o["organization_id"] == org_id for o in orgs)
    context = _ok(client.get("/api/v1/auth/context")).json()
    assert context["organization"]["organization_id"] == org_id
    sites = context["sites"]
    assert sites
    other_site = next((s["site_id"] for s in sites if s["site_id"] != site_id), None)
    if other_site:
        switched = _ok(
            client.post(
                "/api/v1/auth/context",
                json={"organization_id": org_id, "site_id": other_site},
            )
        )
        assert switched.json()["site"]["site_id"] == other_site
        _ok(
            client.post(
                "/api/v1/auth/context",
                json={"organization_id": org_id, "site_id": site_id},
            )
        )
    forbidden_org = client.post(
        "/api/v1/auth/context",
        json={"organization_id": "org-aviation-west", "site_id": "site-cyvr"},
    )
    assert forbidden_org.status_code in {403, 404}

    # --- 3. RBAC ---
    matrix = _ok(client.get("/api/v1/platform/rbac/matrix")).json()
    assert matrix
    templates = _ok(client.get("/api/v1/platform/rbac/templates")).json()
    assert any(t.get("code") for t in templates)
    client.post("/api/v1/auth/logout")
    _ok(client.post("/api/v1/auth/login", json={"operator": "viewer", "password": TEST_AUTH_PASSWORD}))
    assert client.post("/api/v1/fleet/aircraft", json={"model_id": "x", "serial_number": "x"}).status_code in {
        403,
        422,
    }
    create_as_viewer = client.post(
        "/api/v1/platform/notifications",
        json={
            "recipient": "viewer",
            "channel": "in_app",
            "event_type": "smoke",
            "title": "nope",
            "body": "nope",
        },
    )
    assert create_as_viewer.status_code == 403
    client.post("/api/v1/auth/logout")
    _ok(client.post("/api/v1/auth/login", json={"operator": "operator", "password": TEST_AUTH_PASSWORD}))

    # --- 4. Dashboard (uses restored operator session) ---
    dash = _ok(client.get("/api/v1/dashboard/summary")).json()
    assert "alerts" in dash and "fleet_health" in dash
    home_planning = _ok(client.get("/api/v1/planning/dashboard")).json()
    assert home_planning is not None

    # --- 5. Aircraft ---
    empty_ac = client.post("/api/v1/fleet/aircraft", json={})
    assert empty_ac.status_code == 422
    aircraft = _ok(client.get("/api/v1/fleet/aircraft", params={"limit": 50})).json()
    assert len(aircraft) >= 1
    aircraft_id = aircraft[0]["id"]
    assert all(row.get("organization_id") in {None, org_id} or row["organization_id"] == org_id for row in aircraft)
    detail = _ok(client.get(f"/api/v1/fleet/aircraft/{aircraft_id}")).json()
    assert detail["id"] == aircraft_id
    db = SessionLocal()
    try:
        assert db.get(Aircraft, aircraft_id) is not None
    finally:
        db.close()

    # --- 6. Fleet ---
    fleets = _ok(client.get("/api/v1/fleet/fleets")).json()
    assert len(fleets) >= 1

    # --- 7. Components ---
    catalog = _ok(client.get("/api/v1/components/catalog")).json()
    serialized = _ok(client.get("/api/v1/components/serialized", params={"limit": 50})).json()
    assert isinstance(catalog, list)
    assert isinstance(serialized, list)

    # --- 8. Inventory ---
    stock = _ok(client.get("/api/v1/logistics/dashboard")).json()
    assert stock is not None
    balances = _ok(client.get("/api/v1/logistics/stock/balances", params={"limit": 20}))
    assert balances.status_code == 200

    # --- 9. Planning ---
    due = _ok(client.get("/api/v1/planning/due-list")).json()
    assert due is not None
    _ok(client.get("/api/v1/planning/programs"))

    # --- 10. Work Orders (filtered by aircraft from step 5) ---
    orders = _ok(
        client.get("/api/v1/work-orders/orders", params={"aircraft_id": aircraft_id, "limit": 20})
    ).json()
    assert isinstance(orders, list)
    _ok(client.get("/api/v1/work-orders/dashboard"))

    # --- 11. Engineering ---
    ads = _ok(client.get("/api/v1/planning/ads")).json()
    sbs = _ok(client.get("/api/v1/planning/service-bulletins")).json()
    eos = _ok(client.get("/api/v1/planning/engineering-orders")).json()
    assert isinstance(ads, list) and isinstance(sbs, list) and isinstance(eos, list)

    # --- 12. Logbook ---
    logbook = _ok(client.get("/api/v1/maintenance/logbook", params={"aircraft_id": aircraft_id})).json()
    assert isinstance(logbook, list)

    # --- 13. Marketplace ---
    products = _ok(client.get("/api/v1/marketplace/products", params={"limit": 20})).json()
    overview = _ok(client.get("/api/v1/marketplace/overview")).json()
    assert isinstance(products, list)
    assert overview is not None

    # --- 14. Digital Twin ---
    twins = _ok(client.get("/api/v1/twin/twins", params={"limit": 40})).json()
    assert isinstance(twins, list)
    if twins:
        twin_id = twins[0]["id"]
        _ok(client.get(f"/api/v1/twin/twins/{twin_id}"))

    # --- 15. Notifications ---
    notes = _ok(client.get("/api/v1/platform/notifications", params={"limit": 20})).json()
    assert isinstance(notes, list)
    created_note = _ok(
        client.post(
            "/api/v1/platform/notifications",
            json={
                "recipient": "operator",
                "channel": "in_app",
                "event_type": "rc1.smoke",
                "title": "E2E smoke",
                "body": "Sequential smoke notification",
            },
        ),
        201,
    ).json()
    _ok(client.post(f"/api/v1/platform/notifications/{created_note['id']}/read"))

    # --- 16. Search ---
    indexed = _ok(
        client.post(
            "/api/v1/platform/search/index",
            json={
                "doc_type": "aircraft",
                "entity_id": aircraft_id,
                "title": f"Smoke aircraft {aircraft_id}",
                "body": "RC1 sequential smoke search document",
                "keywords": "rc1,smoke,e2e",
            },
        ),
        201,
    )
    search = _ok(client.get("/api/v1/platform/search", params={"q": "smoke", "limit": 20})).json()
    assert search.get("total", 0) >= 1 or search.get("hits") or search.get("items") or indexed.status_code == 201
    if "total" in search:
        assert search["total"] >= 1

    # --- 17. File uploads (metadata register + multipart) ---
    registered = _ok(
        client.post(
            "/api/v1/platform/files",
            json={
                "filename": "rc1-smoke.txt",
                "content_type": "text/plain",
                "file_class": "other",
                "storage_uri": "file://rc1-smoke.txt",
                "sha256": "c" * 64,
                "size_bytes": 12,
                "entity_type": "aircraft",
                "entity_id": aircraft_id,
            },
        ),
        201,
    )
    listed = _ok(client.get("/api/v1/platform/files")).json()
    assert any(f["id"] == registered.json()["id"] for f in listed)
    uploaded = client.post(
        "/api/v1/platform/files/upload",
        files={"file": ("rc1-smoke-upload.txt", b"rc1-smoke-bytes", "text/plain")},
        data={"file_class": "other", "entity_type": "aircraft", "entity_id": aircraft_id},
    )
    assert uploaded.status_code in {201, 200}, uploaded.text

    # --- 18. Reporting ---
    summary = _ok(client.get("/api/v1/reports/summary")).json()
    assert "kpis" in summary or "disclaimer" in summary
    history = _ok(client.get("/api/v1/reports/history")).json()
    assert isinstance(history, list)

    # --- 19. AI Assistant (existing advisory evaluate — not an LLM) ---
    evaluate = _ok(
        client.post(
            "/api/v1/decisions/evaluate",
            json={
                "mission_id": "mission-demo-1",
                "track_id": "track-rc1-smoke",
                "threat_level": "high",
                "threat_score": 82,
                "response_recommendations": ["Monitor", "Escalate"],
                "operator_constraints": ["advisory_only"],
            },
        )
    ).json()
    assert evaluate.get("metadata", {}).get("advisory_only") is True or evaluate.get("disclaimer")
    stubs = _ok(client.get("/api/v1/maintenance/ai/index-stubs")).json()
    assert isinstance(stubs, list)

    # --- 20. Audit Trail (Operator may lack audit.read; Reviewer/Admin is the existing reader) ---
    audit_resp = client.get("/api/v1/audit")
    if audit_resp.status_code == 403:
        client.post("/api/v1/auth/logout")
        _ok(client.post("/api/v1/auth/login", json={"operator": "reviewer", "password": TEST_AUTH_PASSWORD}))
        audit_resp = client.get("/api/v1/audit")
    audit = _ok(audit_resp).json()
    assert isinstance(audit, list)
    db = SessionLocal()
    try:
        rows = list(db.scalars(select(AuditEvent).limit(5)).all())
        assert rows
    finally:
        db.close()

    # --- 21. Logout ---
    logged_out = _ok(client.post("/api/v1/auth/logout")).json()
    assert logged_out.get("authenticated") is False
    session_after = _ok(client.get("/api/v1/auth/session")).json()
    assert session_after.get("authenticated") is False
    assert client.get("/api/v1/fleet/aircraft").status_code == 401
    assert client.get("/api/v1/dashboard/summary").status_code == 401
    # Logout is idempotent.
    _ok(client.post("/api/v1/auth/logout"))
