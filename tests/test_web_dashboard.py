import pytest
from pathlib import Path
import json
from datetime import datetime, timedelta
from unittest.mock import patch

from configstream.web_dashboard import create_app
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

def test_api_export_unsupported_format(client):
    """Test that an unsupported export format returns an error."""
    response = client.get("/api/export/xml")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Unsupported format: xml"}


def test_home_page(client):
    """Test the home page."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Intelligent VPN Configuration Manager" in response.data


def test_dashboard_page(client):
    """Test the dashboard page."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_scheduler_page(client):
    """Test the scheduler page."""
    response = client.get("/scheduler")
    assert response.status_code == 200
    assert b"Scheduler" in response.data


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


def test_api_docs_page(client):
    """Test the API docs page."""
    response = client.get("/api-docs")
    assert response.status_code == 200
    assert b"API Documentation" in response.data


def test_export_page(client):
    """Test the export page."""
    response = client.get("/export")
    assert response.status_code == 200
    assert b"Export Configurations" in response.data


def test_export_page_with_filters(client):
    """Test the export page with filters."""
    with patch("configstream.web_dashboard.get_current_results") as mock_get_results:
        mock_get_results.return_value = {"nodes": []}
        response = client.get("/export?protocol=VLESS&country=US")
        assert response.status_code == 200
        assert b"Export Configurations" in response.data
