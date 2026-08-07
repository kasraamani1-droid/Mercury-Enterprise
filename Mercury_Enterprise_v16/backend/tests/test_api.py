from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_incidents_exist():
    response = client.get('/api/v1/incidents')
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_platform_status():
    response=client.get('/api/v1/platform/status')
    assert response.status_code==200
    assert response.json()['version']=='16.0.0'

def test_integrations_catalog():
    response=client.get('/api/v1/integrations')
    assert response.status_code==200
    assert response.json()['configured']==12

def test_ready():
    response = client.get('/api/v1/ready')
    assert response.status_code == 200
    assert response.json()['ready'] is True


def test_dashboard_summary():
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


def test_websocket_connects():
    with client.websocket_connect('/api/v1/ws') as websocket:
        first = websocket.receive_json()
        assert first['type'] == 'connected'
        websocket.send_text('ping')
        pong = websocket.receive_json()
        assert pong['type'] == 'pong'
