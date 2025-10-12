import pytest
from unittest.mock import patch
from flask import Flask
from configstream.api import api
from configstream.web_dashboard import DashboardData, TestScheduler
from configstream.config import Settings

from pathlib import Path

@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["dashboard_data"] = DashboardData(Path("/tmp"))
    app.config["scheduler"] = TestScheduler(Settings(), Path("/tmp"))
    app.config["settings"] = Settings()
    app.register_blueprint(api, url_prefix='/api')
    with app.test_client() as client:
        yield client

def test_api_current_error(client):
    """Test the /api/current endpoint with an error."""
    with patch.object(client.application.config["dashboard_data"], "get_current_results", side_effect=Exception("Test error")):
        response = client.get("/api/current")
        assert response.status_code == 500
        assert response.get_json() == {"error": "Test error"}

def test_api_history_error(client):
    """Test the /api/history endpoint with an error."""
    with patch.object(client.application.config["dashboard_data"], "get_history", side_effect=Exception("Test error")):
        response = client.get("/api/history")
        assert response.status_code == 500
        assert response.get_json() == {"error": "Test error"}

def test_api_statistics_error(client):
    """Test the /api/statistics endpoint with an error."""
    with patch.object(client.application.config["dashboard_data"], "get_current_results", side_effect=Exception("Test error")):
        response = client.get("/api/statistics")
        assert response.status_code == 500
        assert response.get_json() == {"error": "Test error"}

def test_api_export_error(client):
    """Test the /api/export endpoint with an error."""
    with patch.object(client.application.config["dashboard_data"], "get_current_results", side_effect=Exception("Test error")):
        response = client.get("/api/export/csv")
        assert response.status_code == 500
        assert response.get_json() == {"error": "Test error"}

def test_api_logs_no_key(client):
    """Test the /api/logs endpoint without an API key."""
    client.application.config["settings"].security.api_key = "test"
    response = client.get("/api/logs")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}

def test_api_scheduler_jobs_no_key(client):
    """Test the /api/scheduler/jobs endpoint without an API key."""
    client.application.config["settings"].security.api_key = "test"
    response = client.get("/api/scheduler/jobs")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}

def test_api_settings_invalid_json(client):
    """Test the /api/settings endpoint with invalid JSON."""
    response = client.post("/api/settings", data="not json")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid JSON"}
