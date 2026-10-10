from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_analyze_supported_claim() -> None:
    payload = {
        'headline': 'Free shipping on every order',
        'description': 'We deliver worldwide with speed and convenience.',
        'landing_page_text': 'Shipping is available for only $9.99. We do not offer free shipping.',
        'mock_mode': True,
        'guest_session': True,
    }
    response = client.post('/api/analyze', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['mode'] == 'SIMULATED'
    assert data['simulated'] is True
    assert data['overall_score'] >= 0


def test_invalid_url_is_rejected() -> None:
    payload = {
        'headline': 'Free shipping',
        'landing_page_url': 'javascript:alert(1)',
        'mock_mode': True,
    }
    response = client.post('/api/analyze', json=payload)
    assert response.status_code == 400


def test_upload_rejects_invalid_file() -> None:
    response = client.post('/api/upload', files={'file': ('bad.txt', b'not-a-binary', 'text/plain')})
    assert response.status_code == 200
    assert response.json()['valid'] is True

    bad_response = client.post('/api/upload', files={'file': ('bad.exe', b'\x00\x00\x00\x00', 'application/x-msdownload')})
    assert bad_response.status_code == 400
