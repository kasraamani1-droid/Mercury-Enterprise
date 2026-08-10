from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def login_as(operator: str):
    response = client.post('/api/v1/auth/login', json={'operator': operator, 'password': TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()


def test_audit_created_on_incident_create_with_operator_attribution():
    login_as('operator')
    created = client.post(
        '/api/v1/incidents',
        json={'title': 'Audit attribution incident', 'severity': 'low', 'summary': 'task16'},
    )
    assert created.status_code == 201
    incident_id = created.json()['id']

    login_as('reviewer')
    audit = client.get('/api/v1/audit', params={'action': 'incident.create', 'target_id': incident_id})
    assert audit.status_code == 200
    rows = audit.json()
    assert len(rows) >= 1
    row = rows[0]
    assert row['actor'] == 'operator'
    assert row['actor_role'] == 'Operator'
    assert row['action'] == 'incident.create'
    assert row['target_id'] == incident_id
    assert row['origin'] == 'operator'


def test_approval_trail_request_approve_and_consume():
    login_as('operator')
    incident = client.post(
        '/api/v1/incidents',
        json={'title': 'Approval trail incident', 'severity': 'medium', 'summary': 'task16'},
    )
    assert incident.status_code == 201
    incident_id = incident.json()['id']

    req = client.post(
        '/api/v1/approvals',
        json={'action': 'incident.resolve', 'target_id': incident_id, 'reason': 'Need review'},
    )
    assert req.status_code == 200
    approval_id = req.json()['approval_id']

    login_as('reviewer')
    approved = client.post(f'/api/v1/approvals/{approval_id}/approve')
    assert approved.status_code == 200

    login_as('operator')
    resolved = client.patch(
        f'/api/v1/incidents/{incident_id}/status',
        json={'status': 'resolved', 'approval_id': approval_id},
    )
    assert resolved.status_code == 200

    login_as('reviewer')
    actions = {row['action'] for row in client.get('/api/v1/audit', params={'limit': 200}).json()}
    assert 'approval.request' in actions
    assert 'approval.approve' in actions
    assert 'approval.consume' in actions


def test_evidence_provenance_and_site_stamp():
    login_as('operator')
    incident = client.post(
        '/api/v1/incidents',
        json={'title': 'Evidence provenance incident', 'severity': 'low', 'summary': 'task16'},
    )
    incident_id = incident.json()['id']
    session = client.get('/api/v1/auth/session').json()

    evidence = client.post(
        f'/api/v1/incidents/{incident_id}/evidence',
        json={
            'evidence_type': 'operator_note',
            'source': 'Operator Console',
            'title': 'Note',
            'content': 'Observed UAV',
            'confidence': 88,
        },
    )
    assert evidence.status_code == 201
    body = evidence.json()
    assert body['provenance'] == 'operator_entered'
    assert body['created_by'] == 'operator'
    assert body['organization_id'] == session['organization_id']
    assert body['site_id'] == session['site_id']


def test_audit_list_is_site_scoped():
    login_as('operator')
    context = client.get('/api/v1/auth/context').json()
    organization_id = context['organization']['organization_id']
    sites = context['sites']
    site_a = context['site']['site_id']
    site_b = next((s['site_id'] for s in sites if s['site_id'] != site_a), None)
    assert site_b is not None

    created = client.post(
        '/api/v1/incidents',
        json={'title': f'Site scope {site_a}', 'severity': 'low', 'summary': 'task16'},
    )
    assert created.status_code == 201
    incident_id = created.json()['id']

    login_as('reviewer')
    client.post('/api/v1/auth/context', json={'organization_id': organization_id, 'site_id': site_a})
    on_a = client.get('/api/v1/audit', params={'action': 'incident.create', 'target_id': incident_id})
    assert on_a.status_code == 200
    assert any(row['target_id'] == incident_id for row in on_a.json())

    client.post('/api/v1/auth/context', json={'organization_id': organization_id, 'site_id': site_b})
    on_b = client.get('/api/v1/audit', params={'action': 'incident.create', 'target_id': incident_id})
    assert on_b.status_code == 200
    assert all(row['target_id'] != incident_id for row in on_b.json())


def test_audit_read_forbidden_for_viewer():
    login_as('viewer')
    response = client.get('/api/v1/audit')
    assert response.status_code == 403


def test_audit_read_forbidden_for_operator():
    login_as('operator')
    response = client.get('/api/v1/audit')
    assert response.status_code == 403


def test_audit_read_allowed_for_reviewer():
    login_as('reviewer')
    response = client.get('/api/v1/audit')
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_audit_read_allowed_for_admin():
    login_as('admin')
    response = client.get('/api/v1/audit')
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_audit_unauthorized_without_session():
    client.post('/api/v1/auth/logout')
    response = client.get('/api/v1/audit')
    assert response.status_code == 401


def test_seed_evidence_provenance_is_simulated():
    login_as('operator')
    incidents = client.get('/api/v1/incidents')
    assert incidents.status_code == 200
    assert len(incidents.json()) >= 1
    seeded = []
    for incident in incidents.json():
        detail = client.get(f'/api/v1/incidents/{incident["id"]}')
        assert detail.status_code == 200
        for item in detail.json().get('evidence') or []:
            assert 'provenance' in item
            if item.get('created_by') == 'seed':
                seeded.append(item)
    assert len(seeded) >= 1
    assert all(item['provenance'] == 'simulated' for item in seeded)
