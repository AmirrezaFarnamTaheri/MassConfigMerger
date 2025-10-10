"""Test web dashboard routes."""
import json
import pytest
from pathlib import Path
from configstream.web_dashboard import app, dashboard_data


@pytest.fixture
def client():
    """Create a test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def setup_test_data(tmp_path):
    """Create test data files."""
    # Set dashboard data to use temp directory
    dashboard_data.data_dir = tmp_path
    dashboard_data.current_file = tmp_path / "current_results.json"
    dashboard_data.history_file = tmp_path / "history.jsonl"

    # Create sample data
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

    dashboard_data.current_file.write_text(json.dumps(test_data))

    return test_data


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
    assert response.content_type == 'text/csv; charset=utf-8'

    # Check CSV contains data
    csv_content = response.data.decode('utf-8')
    assert 'protocol' in csv_content
    assert 'vmess' in csv_content

    print("✓ CSV export works")


def test_api_export_json(client, setup_test_data):
    """Test JSON export."""
    response = client.get('/api/export/json')
    assert response.status_code == 200
    assert response.content_type == 'application/json'

    # Check JSON is valid
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 3

    print("✓ JSON export works")


from datetime import datetime

@pytest.mark.parametrize(
    "endpoint", ["/api/current", "/api/history", "/api/statistics", "/api/export/csv"]
)
def test_api_endpoints_general_exception(client, setup_test_data, monkeypatch, endpoint):
    """Test that API endpoints handle general exceptions gracefully."""
    # Mock a function inside the route to raise an exception
    if endpoint in ["/api/current", "/api/statistics", "/api/export/csv"]:
        monkeypatch.setattr(
            "configstream.web_dashboard.dashboard_data.get_current_results",
            lambda: exec('raise Exception("Test Exception")'),
        )
    elif endpoint == "/api/history":
        monkeypatch.setattr(
            "configstream.web_dashboard.dashboard_data.get_history",
            lambda hours: exec('raise Exception("Test Exception")'),
        )

    response = client.get(endpoint)
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Test Exception"
    print(f"✓ {endpoint} handles exceptions correctly")


def test_api_export_unsupported_format(client, setup_test_data):
    """Test /api/export with an unsupported format."""
    response = client.get("/api/export/unsupported")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Unsupported format" in data["error"]
    print("✓ /api/export handles unsupported formats")


def test_dashboard_data_current_results_no_file(tmp_path):
    """Test get_current_results when the file doesn't exist."""
    data_dir = tmp_path
    dashboard_data.data_dir = data_dir
    dashboard_data.current_file = data_dir / "non_existent.json"
    results = dashboard_data.get_current_results()
    assert results["nodes"] == []
    assert results["timestamp"] is None
    print("✓ get_current_results handles missing file")


def test_dashboard_data_current_results_invalid_json(tmp_path):
    """Test get_current_results with invalid JSON."""
    data_dir = tmp_path
    dashboard_data.data_dir = data_dir
    dashboard_data.current_file = data_dir / "invalid.json"
    dashboard_data.current_file.write_text("{invalid json}")
    results = dashboard_data.get_current_results()
    assert results["nodes"] == []
    assert results["timestamp"] is None
    print("✓ get_current_results handles invalid JSON")


def test_dashboard_data_history_no_file(tmp_path):
    """Test get_history when the file doesn't exist."""
    data_dir = tmp_path
    dashboard_data.data_dir = data_dir
    dashboard_data.history_file = data_dir / "non_existent.jsonl"
    history = dashboard_data.get_history()
    assert history == []
    print("✓ get_history handles missing file")


def test_dashboard_data_history_invalid_json_line(tmp_path):
    """Test get_history with a line of invalid JSON."""
    data_dir = tmp_path
    dashboard_data.data_dir = data_dir
    dashboard_data.history_file = data_dir / "history.jsonl"
    valid_entry = {"timestamp": datetime.now().isoformat(), "total_tested": 1, "nodes": []}
    with open(dashboard_data.history_file, "w") as f:
        f.write("{invalid json}\n")
        f.write(json.dumps(valid_entry) + "\n")
        f.write("\n") # empty line

    history = dashboard_data.get_history()
    assert len(history) == 1
    assert history[0]["total_tested"] == 1
    print("✓ get_history handles invalid JSON lines")


def test_filter_nodes_invalid_ping(setup_test_data):
    """Test filter_nodes with invalid (non-integer) ping values."""
    nodes = setup_test_data["nodes"]

    # Invalid min_ping should be ignored
    filtered = dashboard_data.filter_nodes(nodes, {"min_ping": "abc"})
    assert len(filtered) == len(nodes)

    # Invalid max_ping should be ignored
    filtered = dashboard_data.filter_nodes(nodes, {"max_ping": "xyz"})
    assert len(filtered) == len(nodes)
    print("✓ filter_nodes ignores invalid ping values")

def test_export_csv_empty(setup_test_data):
    """Test exporting an empty list of nodes to CSV."""
    csv_output = dashboard_data.export_csv([])
    assert csv_output == ""
    print("✓ export_csv handles empty node list")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-s'])