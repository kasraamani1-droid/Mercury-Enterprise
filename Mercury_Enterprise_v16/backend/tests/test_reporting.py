from conftest import TEST_AUTH_PASSWORD
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as(operator: str):
    response = client.post('/api/v1/auth/login', json={'operator': operator, 'password': TEST_AUTH_PASSWORD})
    assert response.status_code == 200
    return response.json()


def test_report_summary_scoped_and_authorized():
    login_as('operator')
    created = client.post(
        '/api/v1/incidents',
        json={'title': 'Report KPI incident', 'severity': 'medium', 'summary': 'task17'},
    )
    assert created.status_code == 201

    login_as('viewer')
    summary = client.get('/api/v1/reports/summary')
    assert summary.status_code == 200
    payload = summary.json()
    assert 'kpis' in payload
    assert payload['kpis']['incidents_total'] >= 1
    assert 'provenance' in payload
    assert 'disclaimer' in payload


def test_report_history_includes_provenance_field():
    login_as('operator')
    incident = client.post(
        '/api/v1/incidents',
        json={'title': 'History provenance incident', 'severity': 'low', 'summary': 'task17'},
    ).json()
    evidence = client.post(
        f"/api/v1/incidents/{incident['id']}/evidence",
        json={
            'evidence_type': 'operator_note',
            'source': 'Operator Console',
            'title': 'Note',
            'content': 'Observed',
            'confidence': 70,
            'provenance': 'operator_entered',
        },
    )
    assert evidence.status_code == 201

    history = client.get('/api/v1/reports/history')
    assert history.status_code == 200
    rows = history.json()
    assert any(row['id'] == incident['id'] and 'operator_entered' in (row.get('provenance') or '') for row in rows)


def test_report_site_scope_excludes_other_site():
    login_as('operator')
    context = client.get('/api/v1/auth/context').json()
    organization_id = context['organization']['organization_id']
    site_a = context['site']['site_id']
    site_b = next(s['site_id'] for s in context['sites'] if s['site_id'] != site_a)

    created = client.post(
        '/api/v1/incidents',
        json={'title': f'Site A only {site_a}', 'severity': 'low', 'summary': 'task17'},
    )
    assert created.status_code == 201
    incident_id = created.json()['id']

    client.post('/api/v1/auth/context', json={'organization_id': organization_id, 'site_id': site_b})
    history_b = client.get('/api/v1/reports/history')
    assert history_b.status_code == 200
    assert all(row['id'] != incident_id for row in history_b.json())

    client.post('/api/v1/auth/context', json={'organization_id': organization_id, 'site_id': site_a})
    history_a = client.get('/api/v1/reports/history')
    assert any(row['id'] == incident_id for row in history_a.json())


def test_report_unauthorized_without_session():
    client.post('/api/v1/auth/logout')
    assert client.get('/api/v1/reports/summary').status_code == 401
