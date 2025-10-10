"""Test web dashboard routes."""
import json
import pytest
from pathlib import Path
from configstream.web_dashboard import create_app
from configstream.config import Settings


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    settings = Settings()
    app = create_app(settings)
    app.config.update({
        "TESTING": True,
    })
    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def setup_test_data(app, tmp_path):
    """Create test data files and configure the app to use them."""
    dashboard_data = app.config["DASHBOARD_DATA"]
    dashboard_data.data_dir = tmp_path
    dashboard_data.current_file = tmp_path / "current_results.json"
    dashboard_data.history_file = tmp_path / "history.jsonl"

    test_data = {
        "timestamp": "2025-10-10T12:00:00",
        "total_tested": 3,
        "successful": 2,
        "failed": 1,
        "nodes": [
            {"config": "vmess://test1", "protocol": "vmess", "ping_ms": 50, "country": "US", "city": "New York", "organization": "Test Org", "ip": "1.2.3.4", "port": 443, "is_blocked": False, "timestamp": "2025-10-10T12:00:00"},
            {"config": "ss://test2", "protocol": "shadowsocks", "ping_ms": 150, "country": "UK", "city": "London", "organization": "Test Org 2", "ip": "5.6.7.8", "port": 8388, "is_blocked": False, "timestamp": "2025-10-10T12:00:00"},
            {"config": "trojan://test3", "protocol": "trojan", "ping_ms": -1, "country": "DE", "city": "Berlin", "organization": "Test Org 3", "ip": "9.10.11.12", "port": 443, "is_blocked": True, "timestamp": "2025-10-10T12:00:00"}
        ]
    }

    dashboard_data.current_file.write_text(json.dumps(test_data))
    return test_data


def test_index_route(client):
    """Test main dashboard page loads."""
    response = client.get('/')
    assert response.status_code == 200


def test_api_current(client, setup_test_data):
    """Test /api/current endpoint."""
    response = client.get('/api/current')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['nodes']) == 3


def test_api_current_with_filters(client, setup_test_data):
    """Test /api/current with filters."""
    response = client.get('/api/current?protocol=vmess')
    data = json.loads(response.data)
    assert len(data['nodes']) == 1
    assert data['nodes'][0]['protocol'] == 'vmess'


def test_api_statistics(client, setup_test_data):
    """Test /api/statistics endpoint."""
    response = client.get('/api/statistics')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['total_nodes'] == 3
    assert data['successful_nodes'] == 2


def test_api_export_csv(client, setup_test_data):
    """Test CSV export."""
    response = client.get('/api/export/csv')
    assert response.status_code == 200
    assert response.content_type == 'text/csv; charset=utf-8'
    assert 'vmess' in response.data.decode('utf-8')


def test_api_export_json(client, setup_test_data):
    """Test JSON export."""
    response = client.get('/api/export/json')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert len(data) == 3