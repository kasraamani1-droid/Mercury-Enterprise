from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app, decision_engine

client = TestClient(app)


def login_as(operator: str):
    response = client.post("/api/v1/auth/login", json={"operator": operator, "password": TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()


def _evaluate_payload(**overrides):
    body = {
        "mission_id": "mission-demo-1",
        "track_id": "track-demo-1",
        "threat_level": "high",
        "threat_score": 82,
        "response_recommendations": ["Dispatch patrol", "Escalate to operations", "Monitor current state"],
        "operator_constraints": ["avoid overreaction"],
    }
    body.update(overrides)
    return body


def test_evaluate_returns_enriched_explanation_payload():
    login_as("operator")
    response = client.post("/api/v1/decisions/evaluate", json=_evaluate_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["requires_human_approval"] is True
    assert body["metadata"]["automatic_execution"] is False
    assert body["metadata"]["advisory_only"] is True
    assert body["disclaimer"]
    assert isinstance(body["assumptions"], list)
    assert isinstance(body["uncertainty"], list)
    assert isinstance(body["factor_breakdown"], list)
    assert isinstance(body["warnings"], list)
    assert isinstance(body["ranked_actions"], list)
    assert len(body["ranked_actions"]) >= 1
    assert body["ranked_actions"][0]["overall_score"] >= body["ranked_actions"][-1]["overall_score"]
    assert body["selected_recommendation"]["name"] == body["ranked_actions"][0]["name"]
    assert body["organization_id"]
    assert body["site_id"]
    assert body["review"]["state"] == "pending"
    assert "connector_context" in body


def test_evaluate_requires_auth_and_permission_shape():
    client.post("/api/v1/auth/logout")
    unauth = client.post("/api/v1/decisions/evaluate", json=_evaluate_payload())
    assert unauth.status_code == 401


def test_review_happy_path_and_audit():
    login_as("operator")
    created = client.post("/api/v1/decisions/evaluate", json=_evaluate_payload(track_id="track-review-1")).json()
    decision_id = created["decision_id"]

    reviewed = client.post(
        f"/api/v1/decisions/{decision_id}/review",
        json={"state": "acknowledged", "comment": "Operator reviewed alternatives"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["review"]["state"] == "acknowledged"
    assert reviewed.json()["review"]["reviewed_by"] == "operator"

    login_as("reviewer")
    actions = {row["action"] for row in client.get("/api/v1/audit", params={"limit": 200}).json()}
    assert "decision.evaluate" in actions
    assert "decision.review" in actions


def test_review_invalid_transition_and_comment_required():
    login_as("operator")
    decision_id = client.post("/api/v1/decisions/evaluate", json=_evaluate_payload(track_id="track-review-2")).json()[
        "decision_id"
    ]

    missing_comment = client.post(
        f"/api/v1/decisions/{decision_id}/review",
        json={"state": "commented"},
    )
    assert missing_comment.status_code == 422

    commented = client.post(
        f"/api/v1/decisions/{decision_id}/review",
        json={"state": "commented", "comment": "Need more sensor confirmation"},
    )
    assert commented.status_code == 200

    terminal = client.post(
        f"/api/v1/decisions/{decision_id}/review",
        json={"state": "acknowledged"},
    )
    assert terminal.status_code == 200

    again = client.post(
        f"/api/v1/decisions/{decision_id}/review",
        json={"state": "rejected_advisory"},
    )
    assert again.status_code == 409


def test_viewer_cannot_review_but_can_read():
    login_as("operator")
    decision_id = client.post("/api/v1/decisions/evaluate", json=_evaluate_payload(track_id="track-viewer-1")).json()[
        "decision_id"
    ]

    login_as("viewer")
    listed = client.get("/api/v1/decisions")
    assert listed.status_code == 200
    assert any(item["decision_id"] == decision_id for item in listed.json())

    forbidden = client.post(
        f"/api/v1/decisions/{decision_id}/review",
        json={"state": "acknowledged"},
    )
    assert forbidden.status_code == 403


def test_site_scoped_get_hides_other_site_decision():
    login_as("operator")
    created = client.post("/api/v1/decisions/evaluate", json=_evaluate_payload(track_id="track-scope-1")).json()
    decision_id = created["decision_id"]
    org_id = created["organization_id"]

    # Mutate stored site to simulate foreign-site decision without second org bootstrap.
    stored = decision_engine.get_decision(decision_id)
    assert stored is not None
    stored["site_id"] = "site-foreign"
    decision_engine._decision_store[decision_id] = stored

    missing = client.get(f"/api/v1/decisions/{decision_id}")
    assert missing.status_code == 404

    # Restore for other tests / cleanup
    stored["site_id"] = created["site_id"]
    stored["organization_id"] = org_id
    decision_engine._decision_store[decision_id] = stored


def test_dashboard_summary_includes_additive_decision_keys():
    login_as("operator")
    client.post("/api/v1/decisions/evaluate", json=_evaluate_payload(track_id="track-dash-1"))
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    decisions = response.json()["decisions"]
    assert "pending_human_review" in decisions
    assert "warning_count" in decisions
    assert "alternative_count" in decisions
    assert "latest_decision_id" in decisions
    assert "latest_review_state" in decisions
    assert decisions["advisory_only"] is True
    timeline = response.json()["decision_timeline"]
    assert timeline
    assert "decision_id" in timeline[0]
    assert "review_state" in timeline[0]
