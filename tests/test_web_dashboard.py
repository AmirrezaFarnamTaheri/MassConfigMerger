import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import json
from datetime import datetime

from configstream.web_dashboard import DashboardData, create_app, run_dashboard
from configstream.config import Settings


@pytest.fixture
def dashboard_data(fs) -> DashboardData:
    """Fixture for DashboardData with a fake filesystem."""
    data_dir = Path("/data")
    data_dir.mkdir(exist_ok=True)
    settings = Settings()
    dd = DashboardData(settings)
    dd.data_dir = data_dir
    dd.current_file = data_dir / "current.json"
    dd.history_file = data_dir / "history.jsonl"
    return dd


def test_dashboard_data_get_history_no_file(dashboard_data: DashboardData):
    """Test get_history when the history file does not exist."""
    assert dashboard_data.get_history() == []


def test_dashboard_data_filter_nodes_all_filters(dashboard_data: DashboardData):
    """Test filtering with all possible filter conditions."""
    nodes = [
        {"protocol": "VLESS", "country": "US", "ping_ms": 100, "is_blocked": False, "city": "New York"},
        {"protocol": "SS", "country": "DE", "ping_ms": 200, "is_blocked": True, "organization": "TestOrg"},
        {"protocol": "VLESS", "country": "US", "ping_ms": 50, "is_blocked": False, "ip": "1.1.1.1"},
        {"protocol": "VLESS", "country": "JP", "ping_ms": 150, "is_blocked": False, "city": "Tokyo"},
    ]

    # Test protocol filter
    filtered = dashboard_data.filter_nodes(nodes, {"protocol": "ss"})
    assert len(filtered) == 1
    assert filtered[0]["protocol"] == "SS"

    # Test country filter
    filtered = dashboard_data.filter_nodes(nodes, {"country": "us"})
    assert len(filtered) == 2

    # Test min_ping filter
    filtered = dashboard_data.filter_nodes(nodes, {"min_ping": "120"})
    assert len(filtered) == 2

    # Test max_ping filter
    filtered = dashboard_data.filter_nodes(nodes, {"max_ping": "120"})
    assert len(filtered) == 2

    # Test exclude_blocked filter
    filtered = dashboard_data.filter_nodes(nodes, {"exclude_blocked": "true"})
    assert len(filtered) == 3
    assert all(not n.get("is_blocked") for n in filtered)

    # Test search filter
    filtered = dashboard_data.filter_nodes(nodes, {"search": "testorg"})
    assert len(filtered) == 1
    assert filtered[0]["organization"] == "TestOrg"

    filtered = dashboard_data.filter_nodes(nodes, {"search": "1.1.1.1"})
    assert len(filtered) == 1
    assert filtered[0]["ip"] == "1.1.1.1"

    # Test invalid ping values
    filtered = dashboard_data.filter_nodes(nodes, {"min_ping": "abc"})
    assert len(filtered) == 4 # No change
    filtered = dashboard_data.filter_nodes(nodes, {"max_ping": "xyz"})
    assert len(filtered) == 4 # No change


@patch("configstream.web_dashboard.serve", new_callable=AsyncMock)
@patch("configstream.web_dashboard.create_app")
async def test_run_dashboard(mock_create_app, mock_serve):
    """Test the run_dashboard function."""
    mock_app = MagicMock()
    mock_create_app.return_value = mock_app

    await run_dashboard(host="localhost", port=9999)

    mock_create_app.assert_called_once()
    mock_serve.assert_awaited_once()
    # Check that the config bind address is correct
    config_arg = mock_serve.await_args[0][1]
    assert config_arg.bind == ["localhost:9999"]


@patch("importlib.metadata.version", return_value="3.0.0")
def test_require_api_key_decorator(mock_version, fs):
    """Test the API key decorator logic."""
    settings = Settings()
    settings.security.api_key = "test-key"
    app = create_app(settings=settings)
    client = app.test_client()

    # No key provided
    response = client.get("/api/current")
    assert response.status_code == 401

    # Correct key in X-API-Key header
    response = client.get("/api/current", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200

    # Correct key in Authorization header
    response = client.get("/api/current", headers={"Authorization": "Bearer test-key"})
    assert response.status_code == 200

    # Incorrect key
    response = client.get("/api/current", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401

    # No API key configured
    settings.security.api_key = None
    app = create_app(settings=settings)
    client = app.test_client()
    response = client.get("/api/current")
    assert response.status_code == 200


def test_dashboard_data_export_csv_empty(dashboard_data: DashboardData):
    """Test export_csv with an empty list of nodes."""
    csv_output = dashboard_data.export_csv([])
    assert csv_output == ""


def test_dashboard_data_get_current_results_exists(dashboard_data: DashboardData):
    """Test get_current_results when the results file exists."""
    test_content = {"timestamp": "2023-10-27T10:00:00", "nodes": [{"id": 1}]}
    dashboard_data.current_file.write_text(json.dumps(test_content))
    results = dashboard_data.get_current_results()
    assert results == test_content


def test_dashboard_data_export_json(dashboard_data: DashboardData):
    """Test export_json method."""
    nodes = [{"protocol": "vless", "ping_ms": 100}]
    json_output = dashboard_data.export_json(nodes)
    assert json.loads(json_output) == nodes