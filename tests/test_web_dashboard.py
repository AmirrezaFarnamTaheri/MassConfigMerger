import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
from datetime import datetime, timedelta

from configstream.web_dashboard import DashboardData, app as flask_app


@pytest.fixture
def client():
    """Fixture for a Flask test client."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def dashboard_data(tmp_path):
    """Fixture to create a DashboardData instance with a temporary data directory."""
    data_dir = tmp_path
    # We patch the global `dashboard_data` instance used by the Flask app
    with patch("configstream.web_dashboard.dashboard_data", DashboardData(data_dir)):
        yield DashboardData(data_dir)


def test_get_current_results_no_file(dashboard_data):
    """Test get_current_results when the data file does not exist."""
    results = dashboard_data.get_current_results()
    assert results == {"timestamp": None, "nodes": []}


def test_get_history_filtering(dashboard_data):
    """Test get_history to ensure it correctly filters by time."""
    now = datetime.now()
    old_ts = (now - timedelta(hours=30)).isoformat()
    new_ts = (now - timedelta(hours=1)).isoformat()
    history_file = dashboard_data.history_file
    with open(history_file, "w") as f:
        f.write(json.dumps({"timestamp": old_ts}) + "\n")
        f.write(json.dumps({"timestamp": new_ts}) + "\n")

    history = dashboard_data.get_history(hours=24)
    assert len(history) == 1
    assert history[0]["timestamp"] == new_ts


def test_api_current_endpoint(client, dashboard_data):
    """Test the /api/current endpoint."""
    test_data = {"timestamp": datetime.now().isoformat(), "nodes": [{"protocol": "VLESS"}]}
    dashboard_data.current_file.write_text(json.dumps(test_data))

    response = client.get("/api/current")
    assert response.status_code == 200
    json_response = response.get_json()
    assert json_response["nodes"][0]["protocol"] == "VLESS"


def test_api_export_csv(client, dashboard_data):
    """Test the CSV export functionality."""
    nodes = [{"protocol": "vless", "country": "US", "ping_ms": 100}]
    test_data = {"timestamp": datetime.now().isoformat(), "nodes": nodes}
    dashboard_data.current_file.write_text(json.dumps(test_data))

    response = client.get("/api/export/csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "protocol,country,ping_ms" in response.data.decode()
    assert "vless,US,100" in response.data.decode()


def test_api_export_unsupported_format(client):
    """Test that an unsupported export format returns an error."""
    response = client.get("/api/export/xml")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Unsupported format"}