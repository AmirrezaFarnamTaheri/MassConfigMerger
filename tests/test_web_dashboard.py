import pytest
from pathlib import Path
import json
from datetime import datetime, timedelta
from unittest.mock import patch

from configstream.web_dashboard import DashboardData, create_app
from configstream.config import Settings

@pytest.fixture
def app(fs, settings):
    """Create and configure a new app instance for each test."""
    fs.add_real_directory(str(Path(__file__).resolve().parents[1] / "src" / "configstream" / "templates"))
    app = create_app(settings)
    app.config.update({"TESTING": True})
    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    with patch("importlib.metadata.version", return_value="3.0.3"):
        yield app.test_client()

def test_dashboard_data_initialization(tmp_path):
    """Test that DashboardData initializes correctly."""
    data_dir = tmp_path
    dashboard_data = DashboardData(data_dir)
    assert dashboard_data.data_dir == data_dir
    assert dashboard_data.current_file == data_dir / "current_results.json"
    assert dashboard_data.history_file == data_dir / "history.jsonl"

def test_get_current_results_file_not_found(tmp_path):
    """Test get_current_results when the file doesn't exist."""
    dashboard_data = DashboardData(tmp_path)
    results = dashboard_data.get_current_results()
    assert results["timestamp"] is None
    assert results["nodes"] == []

def test_get_history_file_not_found(tmp_path):
    """Test get_history when the file doesn't exist."""
    dashboard_data = DashboardData(tmp_path)
    history = dashboard_data.get_history()
    assert history == []

def test_filter_nodes_no_filters():
    """Test that filtering with no filters returns the original node list."""
    dashboard_data = DashboardData(Path("/data"))
    nodes = [{"id": 1}, {"id": 2}]
    filtered = dashboard_data.filter_nodes(nodes, {})
    assert filtered == nodes

def test_export_csv_empty_nodes():
    """Test that exporting an empty list of nodes returns an empty string."""
    dashboard_data = DashboardData(Path("/data"))
    result = dashboard_data.export_csv([])
    assert result == ""

def test_api_export_unsupported_format(client):
    """Test that an unsupported export format returns an error."""
    response = client.get("/api/export/xml")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Unsupported format: xml"}


def test_home_page(client):
    """Test the home page."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to ConfigStream" in response.data


def test_dashboard_page(client):
    """Test the dashboard page."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_system_page(client):
    """Test the system page."""
    response = client.get("/system")
    assert response.status_code == 200
    assert b"System Monitoring" in response.data


def test_settings_page(client):
    """Test the settings page."""
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"Application Settings" in response.data


def test_documentation_page(client):
    """Test the documentation page."""
    response = client.get("/documentation")
    assert response.status_code == 200
    assert b"Documentation" in response.data


def test_quick_start_page(client):
    """Test the quick start page."""
    response = client.get("/quick-start")
    assert response.status_code == 200
    assert b"Quick Start Guide" in response.data


def test_api_docs_page(client):
    """Test the API docs page."""
    response = client.get("/api-docs")
    assert response.status_code == 200
    assert b"API Documentation" in response.data


def test_roadmap_page(client):
    """Test the roadmap page."""
    response = client.get("/roadmap")
    assert response.status_code == 200
    assert b"Project Roadmap" in response.data


def test_export_page(client):
    """Test the export page."""
    response = client.get("/export")
    assert response.status_code == 200
    assert b"Export Configurations" in response.data


@pytest.fixture
def dashboard_data(tmp_path: Path) -> DashboardData:
    """Fixture for DashboardData."""
    return DashboardData(tmp_path)


def test_get_current_results_invalid_json(dashboard_data: DashboardData):
    """Test get_current_results with invalid JSON."""
    results_file = dashboard_data.data_dir / "current_results.json"
    results_file.write_text("invalid json")
    results = dashboard_data.get_current_results()
    assert results["timestamp"] is None
    assert results["nodes"] == []


def test_get_history_invalid_json(dashboard_data: DashboardData):
    """Test get_history with invalid JSON."""
    history_file = dashboard_data.data_dir / "history.jsonl"
    history_file.write_text("invalid json\n")
    history = dashboard_data.get_history()
    assert history == []


def test_filter_nodes(dashboard_data: DashboardData):
    """Test filtering nodes."""
    nodes = [
        {"protocol": "VLESS", "country": "US", "ping_ms": 100, "is_blocked": False, "city": "New York", "organization": "Test", "ip": "1.1.1.1"},
        {"protocol": "SS", "country": "DE", "ping_ms": 200, "is_blocked": True, "city": "Berlin", "organization": "Test", "ip": "2.2.2.2"},
    ]
    filters = {
        "protocol": "VLESS",
        "country": "US",
        "min_ping": "50",
        "max_ping": "150",
        "exclude_blocked": "1",
        "search": "New",
    }
    filtered = dashboard_data.filter_nodes(nodes, filters)
    assert len(filtered) == 1
    assert filtered[0]["protocol"] == "VLESS"

def test_export_page_with_filters(client):
    """Test the export page with filters."""
    with patch("configstream.web_dashboard.DashboardData.get_current_results") as mock_get_results:
        mock_get_results.return_value = {"nodes": []}
        response = client.get("/export?protocol=VLESS&country=US")
        assert response.status_code == 200
        assert b"Export Configurations" in response.data
