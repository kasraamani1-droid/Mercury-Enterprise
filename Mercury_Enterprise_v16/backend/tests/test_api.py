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


def test_websocket_connects():
    with client.websocket_connect('/api/v1/ws') as websocket:
        first = websocket.receive_json()
        assert first['type'] == 'connected'
        websocket.send_text('ping')
        pong = websocket.receive_json()
        assert pong['type'] == 'pong'
