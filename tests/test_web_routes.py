from __future__ import annotations

import zipfile
import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from configstream.config import Settings
from configstream.web import app


@patch("configstream.web.run_aggregation_pipeline", new_callable=AsyncMock)
@patch("configstream.web.load_config")
def test_aggregate_api(mock_load_config, mock_run_pipeline, client, fs):
    """Test the /api/aggregate route."""
    fs.create_file("config.yaml")
    mock_load_config.return_value = Settings()
    mock_run_pipeline.return_value = (Path("/fake/dir"), [Path("/fake/dir/file.txt")])

    response = client.post("/api/aggregate", json={})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["output_dir"] == "/fake/dir"
    assert payload["file_count"] == 1
    assert payload["files"] == ["/fake/dir/file.txt"]
    mock_run_pipeline.assert_awaited_once()


@patch("configstream.web.run_aggregation_pipeline", new_callable=AsyncMock)
@patch("configstream.web.load_config")
def test_aggregate_requires_token(mock_load_config, mock_run_pipeline, client, fs):
    """Ensure /api/aggregate enforces the configured API token."""
    settings = Settings()
    settings.security.web_api_token = "topsecret"
    mock_load_config.return_value = settings

    response = client.post("/api/aggregate", json={})
    assert response.status_code == 401
    assert b"Missing or invalid API token" in response.data
    mock_run_pipeline.assert_not_awaited()

    mock_run_pipeline.reset_mock()
    mock_run_pipeline.return_value = (Path("/secured"), [])
    response_ok = client.post("/api/aggregate", json={}, headers={"X-API-Key": "topsecret"})
    assert response_ok.status_code == 200
    mock_run_pipeline.assert_awaited_once()


@patch("configstream.web.run_merger_pipeline", new_callable=AsyncMock)
@patch("configstream.web.load_config")
def test_merge_route_success(mock_load_config, mock_run_merger, client, fs):
    """Test the /api/merge route when the resume file exists."""
    fs.create_file("pyproject.toml")
    fs.create_dir("fake_output")
    fs.create_file("fake_output/vpn_subscription_raw.txt")
    settings = Settings()
    settings.output.output_dir = Path("fake_output")
    mock_load_config.return_value = settings

    response = client.post("/api/merge", json={})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "merge complete"
    assert payload["resume_file"].endswith("vpn_subscription_raw.txt")
    mock_run_merger.assert_awaited_once()


def test_index_route(client):
    """Test the index route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"ConfigStream Control Panel" in response.data


def test_health_check_route(client):
    """Test the /health route."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


@patch("configstream.web.Database")
def test_history_route_success(MockDatabase, client, fs):
    """Test the /history route with successful data retrieval."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  history_db_file: 'fake.db'")
    fs.create_dir("output")

    mock_db_instance = MockDatabase.return_value
    mock_db_instance.connect = AsyncMock()
    mock_db_instance.close = AsyncMock()
    mock_db_instance.get_proxy_history = AsyncMock(return_value={
        "proxy1": {"successes": 10, "failures": 0, "last_tested": 1672531200, "country": "US"},
    })

    response = client.get("/history")
    assert response.status_code == 200
    assert b"Complete Proxy History" in response.data
    assert b"proxy1" in response.data
    assert b"100.00%" in response.data


def test_sources_route(client, fs):
    """Test the /sources route."""
    fs.create_file("sources.txt", contents="http://source1.com\nhttp://source2.com")
    response = client.get("/sources")
    assert response.status_code == 200
    assert b"Subscription Sources" in response.data
    assert b"http://source1.com" in response.data


def test_analytics_route(client, fs):
    """Test the /analytics route."""
    fs.create_file("proxy_history.db")
    response = client.get("/analytics")
    assert response.status_code == 200
    assert b"Performance Analytics" in response.data


def test_settings_route(client, fs):
    """Test the /settings route."""
    fs.create_file("config.yaml", contents="network:\n  request_timeout: 99")
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"Application Settings" in response.data
    assert b"request_timeout: 99" in response.data


def test_logs_route(client, fs):
    """Test the /logs route."""
    fs.create_file("web_server.log", contents="[INFO] Server started.")
    response = client.get("/logs")
    assert response.status_code == 200
    assert b"Application Logs" in response.data
    assert b"[INFO] Server started." in response.data


def test_backup_route(client):
    """Test the /backup route."""
    response = client.get("/backup")
    assert response.status_code == 200
    assert b"Backup & Restore" in response.data


def test_export_backup_api(client, fs):
    """Test the /api/export-backup endpoint."""
    fs.create_file("config.yaml", contents="test_config")
    fs.create_file("sources.txt", contents="test_sources")
    response = client.get("/api/export-backup")
    assert response.status_code == 200
    assert response.mimetype == "application/zip"

    zip_file = zipfile.ZipFile(io.BytesIO(response.data))
    assert "config.yaml" in zip_file.namelist()
    assert "sources.txt" in zip_file.namelist()


def test_import_backup_api(client, fs):
    """Test the /api/import-backup endpoint."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("config.yaml", "new_config")
    zip_buffer.seek(0)

    response = client.post(
        "/api/import-backup",
        data={"backup_file": (zip_buffer, "backup.zip")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.json["message"] == "Backup imported successfully."
    assert "new_config" in (Path(".") / "config.yaml").read_text()