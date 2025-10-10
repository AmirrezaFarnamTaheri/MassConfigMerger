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
    assert results == {
        "timestamp": None,
        "total_tested": 0,
        "successful": 0,
        "failed": 0,
        "nodes": []
    }

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