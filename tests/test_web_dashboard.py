import json
import pytest
from pathlib import Path
from configstream.web_dashboard import create_app
from configstream.config import Settings, OutputSettings

@pytest.fixture
def settings(tmp_path: Path, monkeypatch) -> Settings:
    """Fixture for a Settings object with a temporary data directory."""
    monkeypatch.chdir(tmp_path)
    data_dir = Path("data")
    data_dir.mkdir()

    settings = Settings()
    settings.output = OutputSettings(
        current_results_file=data_dir / "current_results.json",
        history_file=data_dir / "history.jsonl",
        output_dir=data_dir,
    )

    # Create sample data
    test_data = {
        "timestamp": "2025-10-10T12:00:00",
        "total_tested": 3,
        "successful": 2,
        "failed": 1,
        "nodes": [
            {
                "config": "vmess://test1", "protocol": "vmess", "ping_time": 50,
                "country": "US", "city": "New York", "organization": "Test Org",
                "host": "1.2.3.4", "port": 443, "is_blocked": False,
                "timestamp": "2025-10-10T12:00:00"
            },
            {
                "config": "ss://test2", "protocol": "shadowsocks", "ping_time": 150,
                "country": "UK", "city": "London", "organization": "Test Org 2",
                "host": "5.6.7.8", "port": 8388, "is_blocked": False,
                "timestamp": "2025-10-10T12:00:00"
            },
            {
                "config": "trojan://test3", "protocol": "trojan", "ping_time": -1,
                "country": "DE", "city": "Berlin", "organization": "Test Org 3",
                "host": "9.10.11.12", "port": 443, "is_blocked": True,
                "timestamp": "2025-10-10T12:00:00"
            }
        ]
    }
    settings.output.current_results_file.write_text(json.dumps(test_data))

    return settings

@pytest.fixture
def app(settings: Settings):
    """Fixture for a Flask app instance."""
    app = create_app(settings=settings)
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    """Fixture for a Flask test client."""
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Test main dashboard page loads."""
    response = client.get('/')
    assert response.status_code == 200

def test_api_current(client):
    """Test /api/current endpoint."""
    response = client.get('/api/current')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['total_tested'] == 3
    assert data['successful'] == 2
    assert data['failed'] == 1
    assert len(data['nodes']) == 3

def test_api_current_with_filters(client):
    """Test /api/current with filters."""
    # Test protocol filter
    response = client.get('/api/current?protocol=vmess')
    data = json.loads(response.data)
    assert len(data['nodes']) == 1
    assert data['nodes'][0]['protocol'] == 'vmess'

    # Test country filter
    response = client.get('/api/current?country=UK')
    data = json.loads(response.data)
    assert len(data['nodes']) == 1
    assert data['nodes'][0]['country'] == 'UK'

    # Test combined filters
    response = client.get('/api/current?protocol=shadowsocks&country=UK')
    data = json.loads(response.data)
    assert len(data['nodes']) == 1
    assert data['nodes'][0]['protocol'] == 'shadowsocks'
    assert data['nodes'][0]['country'] == 'UK'

def test_get_current_results_malformed_json(settings: Settings):
    """Test that get_current_results handles malformed JSON."""
    settings.output.current_results_file.write_text("{malformed_json")
    app = create_app(settings=settings)
    with app.test_client() as client:
        response = client.get('/api/current')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['nodes'] == []
        assert data['total_tested'] == 0

def test_api_statistics(client):
    """Test /api/statistics endpoint."""
    response = client.get('/api/statistics')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['total_nodes'] == 3
    assert data['successful_nodes'] == 2
    assert 'protocols' in data
    assert 'countries' in data

def test_api_export_csv(client):
    """Test CSV export."""
    response = client.get('/api/export/csv')
    assert response.status_code == 200
    assert response.content_type == 'text/csv; charset=utf-8'
    assert 'vmess' in response.data.decode('utf-8')

def test_api_export_json(client):
    """Test JSON export."""
    response = client.get('/api/export/json')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert len(data) == 3