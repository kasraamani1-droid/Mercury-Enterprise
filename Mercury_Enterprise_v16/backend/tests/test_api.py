from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def login_client():
    response = client.post('/api/v1/auth/login', json={'operator': 'operator', 'password': TEST_AUTH_PASSWORD})
    assert response.status_code == 200


def login_as(operator: str):
    response = client.post('/api/v1/auth/login', json={'operator': operator, 'password': TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()

def test_health():
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_incidents_exist():
    login_client()
    response = client.get('/api/v1/incidents')
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_incidents_require_auth():
    client.post('/api/v1/auth/logout')
    response = client.get('/api/v1/incidents')
    assert response.status_code == 401


def test_platform_status():
    login_client()
    response=client.get('/api/v1/platform/status')
    assert response.status_code==200
    assert response.json()['version']=='16.0.0'

def test_integrations_catalog():
    login_client()
    response=client.get('/api/v1/integrations')
    assert response.status_code==200
    assert response.json()['configured']==12

def test_ready():
    response = client.get('/api/v1/ready')
    assert response.status_code == 200
    assert response.json()['ready'] is True


def test_dashboard_summary():
    login_client()
    response = client.get('/api/v1/dashboard/summary')
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        'platform',
        'timeline',
        'services',
        'alerts',
        'missions',
        'decisions',
        'fleet_health',
        'connector_health',
        'ai_confidence_trends',
        'decision_timeline',
        'active_alerts_summary',
        'sensor_health',
    }
    assert payload['platform']['version'] == '16.0.0'
    assert isinstance(payload['timeline']['events'], int)
    assert isinstance(payload['alerts']['total'], int)
    assert isinstance(payload['missions']['active'], int)
    assert isinstance(payload['decisions']['pending_human_review'], int)
    assert isinstance(payload['fleet_health']['incidents'], int)
    assert isinstance(payload['connector_health']['ml_engine'], str)
    assert isinstance(payload['ai_confidence_trends']['samples'], list)
    assert isinstance(payload['decision_timeline'], list)
    assert isinstance(payload['active_alerts_summary']['active'], int)
    assert isinstance(payload['sensor_health']['offline'], int)


def test_login_failure():
    response = client.post('/api/v1/auth/login', json={'operator': 'operator', 'password': 'wrong'})
    assert response.status_code == 401


def test_session_status_and_logout():
    login_client()
    session = client.get('/api/v1/auth/session')
    assert session.status_code == 200
    assert session.json()['authenticated'] is True
    assert session.json()['operator'] == 'operator'
    assert session.json()['role'] == 'Operator'
    assert isinstance(session.json()['organization_id'], str)
    assert isinstance(session.json()['site_id'], str)

    logout = client.post('/api/v1/auth/logout')
    assert logout.status_code == 200
    assert logout.json()['authenticated'] is False

    session_after = client.get('/api/v1/auth/session')
    assert session_after.status_code == 200
    assert session_after.json()['authenticated'] is False


def test_protected_incident_write_requires_session():
    client.post('/api/v1/auth/logout')
    unauthorized = client.post('/api/v1/incidents', json={'title': 'Auth test incident', 'severity': 'low', 'summary': 'session required'})
    assert unauthorized.status_code == 401

    login_client()
    authorized = client.post('/api/v1/incidents', json={'title': 'Auth test incident', 'severity': 'low', 'summary': 'session required'})
    assert authorized.status_code == 201


def test_websocket_connects():
    login_client()
    with client.websocket_connect('/api/v1/ws') as websocket:
        first = websocket.receive_json()
        assert first['type'] == 'connected'
        assert first['operator'] == 'operator'
        assert isinstance(first['organization']['organization_id'], str)
        assert isinstance(first['site']['site_id'], str)
        websocket.send_text('ping')
        pong = websocket.receive_json()
        assert pong['type'] == 'pong'


def test_session_context_get_and_update():
    login_as('operator')

    context = client.get('/api/v1/auth/context')
    assert context.status_code == 200
    payload = context.json()
    assert payload['operator'] == 'operator'
    assert payload['role'] == 'Operator'
    assert isinstance(payload['organizations'], list)
    assert len(payload['organizations']) >= 1
    assert isinstance(payload['sites'], list)
    assert len(payload['sites']) >= 1

    organization_id = payload['organization']['organization_id']
    sites = payload['sites']
    if len(sites) >= 2:
        next_site = sites[1]['site_id']
    else:
        next_site = sites[0]['site_id']

    updated = client.post('/api/v1/auth/context', json={'organization_id': organization_id, 'site_id': next_site})
    assert updated.status_code == 200
    assert updated.json()['organization']['organization_id'] == organization_id
    assert updated.json()['site']['site_id'] == next_site


def test_role_enforcement_viewer_cannot_create_incident():
    login_as('viewer')
    denied = client.post('/api/v1/incidents', json={'title': 'Viewer denied', 'severity': 'low', 'summary': 'rbac'})
    assert denied.status_code == 403


def test_role_enforcement_operator_can_create_incident():
    login_as('operator')
    allowed = client.post('/api/v1/incidents', json={'title': 'Operator allowed', 'severity': 'low', 'summary': 'rbac'})
    assert allowed.status_code == 201


def test_approval_flow_operator_request_reviewer_approve():
    login_as('operator')
    req = client.post('/api/v1/approvals', json={'action': 'incident.resolve', 'target_id': 'INC-TEST', 'reason': 'Need review'})
    assert req.status_code == 200
    approval_id = req.json()['approval_id']

    pending_for_operator = client.get('/api/v1/approvals')
    assert pending_for_operator.status_code == 403

    login_as('reviewer')
    listing = client.get('/api/v1/approvals?status_filter=pending')
    assert listing.status_code == 200
    assert any(item['approval_id'] == approval_id for item in listing.json())

    approved = client.post(f'/api/v1/approvals/{approval_id}/approve')
    assert approved.status_code == 200
    assert approved.json()['status'] == 'approved'
