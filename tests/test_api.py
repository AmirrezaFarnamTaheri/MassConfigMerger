import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from configstream.api import api
from configstream.scheduler import TestScheduler
from configstream.config import Settings

from pathlib import Path

@pytest.fixture
def client():
    with patch("configstream.api.web_dashboard") as mock_web_dashboard:
        app = Flask(__name__)
        app.config["data_dir"] = Path("/tmp")
        app.config["scheduler"] = TestScheduler(Settings(), Path("/tmp"))
        app.config["settings"] = Settings()
        app.register_blueprint(api, url_prefix='/api')
        with app.test_client() as client:
            client.application.config["web_dashboard"] = mock_web_dashboard
            yield client

def test_api_current_success(client):
    """Test the /api/current endpoint with a successful request."""
    mock_data = {"timestamp": "2023-10-27T10:00:00", "nodes": [{"id": 1, "ping_ms": 100}]}
    client.application.config["web_dashboard"].get_current_results.return_value = mock_data
    response = client.get("/api/current")
    assert response.status_code == 200
    assert response.get_json() == mock_data

def test_api_current_error(client):
    """Test the /api/current endpoint with an error."""
    client.application.config["web_dashboard"].get_current_results.side_effect = Exception("Test error")
    response = client.get("/api/current")
    assert response.status_code == 500
    assert response.get_json() == {"error": "Test error"}

def test_api_history_success(client):
    """Test the /api/history endpoint with a successful request."""
    mock_data = [{"id": 1, "ping_ms": 100}]
    client.application.config["web_dashboard"].get_history.return_value = mock_data
    response = client.get("/api/history")
    assert response.status_code == 200
    assert response.get_json() == mock_data

def test_api_history_error(client):
    """Test the /api/history endpoint with an error."""
    client.application.config["web_dashboard"].get_history.side_effect = Exception("Test error")
    response = client.get("/api/history")
    assert response.status_code == 500
    assert response.get_json() == {"error": "Test error"}

def test_api_statistics_success(client):
    """Test the /api/statistics endpoint with a successful request."""
    mock_data = {"nodes": [{"id": 1, "ping_ms": 100, "protocol": "VLESS", "country_code": "US"}]}
    client.application.config["web_dashboard"].get_current_results.return_value = mock_data
    response = client.get("/api/statistics")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_nodes"] == 1
    assert data["successful_nodes"] == 1
    assert data["protocols"]["VLESS"] == 1
    assert data["countries"]["US"] == 1

def test_api_statistics_error(client):
    """Test the /api/statistics endpoint with an error."""
    client.application.config["web_dashboard"].get_current_results.side_effect = Exception("Test error")
    response = client.get("/api/statistics")
    assert response.status_code == 500
    assert response.get_json() == {"error": "Test error"}

def test_api_export_csv_success(client):
    """Test the /api/export/csv endpoint with a successful request."""
    mock_data = {"nodes": [{"id": 1, "ping_ms": 100, "protocol": "VLESS", "country_code": "US"}]}
    client.application.config["web_dashboard"].get_current_results.return_value = mock_data
    client.application.config["web_dashboard"].export_csv.return_value = "id,ping_ms\n1,100"
    client.application.config["web_dashboard"].filter_nodes.return_value = mock_data["nodes"]
    response = client.get("/api/export/csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert response.data == b"id,ping_ms\n1,100"

def test_api_export_json_success(client):
    """Test the /api/export/json endpoint with a successful request."""
    mock_data = {"nodes": [{"id": 1, "ping_ms": 100, "protocol": "VLESS", "country_code": "US"}]}
    client.application.config["web_dashboard"].get_current_results.return_value = mock_data
    client.application.config["web_dashboard"].filter_nodes.return_value = mock_data["nodes"]
    response = client.get("/api/export/json")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.data == b'{"count": 1, "nodes": [{"id": 1, "ping_ms": 100}]}'

def test_api_export_error(client):
    """Test the /api/export endpoint with an error."""
    client.application.config["web_dashboard"].get_current_results.side_effect = Exception("Test error")
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


def test_api_status(client):
    """Test the /api/status endpoint."""
    with patch("psutil.cpu_percent", return_value=50.0), \
         patch("psutil.virtual_memory") as mock_mem:

        mock_mem.return_value.total = 4 * 1024 * 1024 * 1024
        mock_mem.return_value.used = 1 * 1024 * 1024 * 1024
        mock_mem.return_value.percent = 25.0

        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "uptime" in data
        assert data["cpu"]["percent"] == 50.0
        assert data["memory"]["percent"] == 25.0

def test_api_logs(client, fs):
    """Test the /api/logs endpoint."""
    log_content = "line 1\nline 2\n"
    # The api constructs the path from the app's root_path, so we need to create the file there
    log_path = Path(client.application.root_path).parent / "configstream.log"
    fs.create_file(log_path, contents=log_content)

    response = client.get("/api/logs")
    assert response.status_code == 200
    data = response.get_json()
    assert data["logs"] == ["line 1", "line 2"]

def test_api_logs_file_not_found(client):
    """Test the /api/logs endpoint when the log file does not exist."""
    response = client.get("/api/logs")
    assert response.status_code == 200
    data = response.get_json()
    assert data["logs"] == ["Log file not found."]
