"""Test web dashboard routes."""
import json
import pytest
from pathlib import Path
from configstream.web_dashboard import create_app
from unittest.mock import patch


@pytest.fixture
def app(fs, settings):
    """Create and configure a new app instance for each test."""
    fs.add_real_directory(str(Path(__file__).resolve().parents[1] / "src" / "configstream" / "templates"))
    app = create_app(settings)
    app.config.update({"TESTING": True})
    with patch("importlib.metadata.version", return_value="3.0.3"):
        yield app


import time

@pytest.fixture
def client(app):
    """A test client for the app."""
    time.sleep(0.1)
    return app.test_client()


import copy

@pytest.fixture
def setup_test_data():
    """Mocks the dashboard data source and provides a deep copy of test data."""
    test_data = {
        "timestamp": "2025-10-10T12:00:00",
        "total_tested": 3,
        "successful": 2,
        "failed": 1,
        "nodes": [
            {
                "config": "vmess://test1",
                "protocol": "vmess",
                "ping_ms": 50,
                "country": "US",
                "city": "New York",
                "organization": "Test Org",
                "ip": "1.2.3.4",
                "port": 443,
                "is_blocked": False,
                "timestamp": "2025-10-10T12:00:00"
            },
            {
                "config": "ss://test2",
                "protocol": "shadowsocks",
                "ping_ms": 150,
                "country": "UK",
                "city": "London",
                "organization": "Test Org 2",
                "ip": "5.6.7.8",
                "port": 8388,
                "is_blocked": False,
                "timestamp": "2025-10-10T12:00:00"
            },
            {
                "config": "trojan://test3",
                "protocol": "trojan",
                "ping_ms": -1,
                "country": "DE",
                "city": "Berlin",
                "organization": "Test Org 3",
                "ip": "9.10.11.12",
                "port": 443,
                "is_blocked": True,
                "timestamp": "2025-10-10T12:00:00"
            }
        ]
    }

    # Patch the method to return a new deep copy on each call to ensure test isolation
    with patch("configstream.web_dashboard.DashboardData.get_current_results", side_effect=lambda: copy.deepcopy(test_data)):
        yield copy.deepcopy(test_data)


def test_index_route(client):
    """Test main dashboard page loads."""
    response = client.get('/')
    assert response.status_code == 200
    print("✓ Dashboard page loads")


def test_api_current(client, setup_test_data):
    """Test /api/current endpoint."""
    response = client.get('/api/current')
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data['total_tested'] == 3
    assert data['successful'] == 2
    assert data['failed'] == 1
    assert len(data['nodes']) == 3

    print("✓ /api/current works correctly")


def test_api_current_with_filters(client, setup_test_data):
    """Test /api/current with filters."""
    # Filter by protocol
    response = client.get('/api/current?protocol=vmess')
    data = json.loads(response.data)
    assert len(data['nodes']) == 1
    assert data['nodes'][0]['protocol'] == 'vmess'
    print("✓ Protocol filter works")

    # Filter by country
    response = client.get('/api/current?country=UK')
    data = json.loads(response.data)
    assert len(data['nodes']) == 1
    assert data['nodes'][0]['country'] == 'UK'
    print("✓ Country filter works")

    # Filter by max ping
    response = client.get('/api/current?max_ping=100')
    data = json.loads(response.data)
    assert all(n['ping_ms'] <= 100 or n['ping_ms'] < 0 for n in data['nodes'])
    print("✓ Max ping filter works")

    # Exclude blocked
    response = client.get('/api/current?exclude_blocked=1')
    data = json.loads(response.data)
    assert all(not n['is_blocked'] for n in data['nodes'])
    print("✓ Exclude blocked filter works")


def test_api_statistics(client, setup_test_data):
    """Test /api/statistics endpoint."""
    response = client.get('/api/statistics')
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data['total_nodes'] == 3
    assert data['successful_nodes'] == 2
    assert 'protocols' in data
    assert 'countries' in data
    assert 'avg_ping_by_country' in data

    print("✓ /api/statistics works correctly")
    print(f"  Protocols: {data['protocols']}")
    print(f"  Countries: {data['countries']}")


def test_api_export_csv(client, setup_test_data):
    """Test CSV export."""
    response = client.get('/api/export/csv')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'

    # Check CSV contains data
    csv_content = response.data.decode('utf-8')
    assert 'protocol' in csv_content
    assert 'vmess' in csv_content

    print("✓ CSV export works")


def test_api_export_json(client, setup_test_data):
    """Test JSON export."""
    response = client.get('/api/export/json')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/json'

    # Check JSON is valid
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 3

    print("✓ JSON export works")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-s'])