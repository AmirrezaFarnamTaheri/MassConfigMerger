from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Note: No need to import pytest, Settings, or app. They are provided by fixtures for most tests.
# We manually create the app for the tests that failed due to fixture/patch ordering.
from configstream.web import create_app


def _setup_test_client(settings):
    """
    Helper to create a test app and client. This is needed to ensure that
    the app is created after mocks are in place, and to handle the pyfakefs
    metadata issue.
    """
    with patch("importlib.metadata.version", return_value="3.0.3"):
        app = create_app(settings_override=settings)
        app.config.update({"TESTING": True})
        client = app.test_client()
    return client


@patch("configstream.web._run_async_task")
def test_aggregate_api(mock_run_async, settings, fs):
    """Test the /api/aggregate route."""
    client = _setup_test_client(settings)
    mock_run_async.return_value = (
        Path(settings.output.output_dir),
        [Path(settings.output.output_dir) / "file.txt"],
    )
    response = client.post(
        "/api/aggregate",
        json={},
        headers={"Authorization": f"Bearer {settings.security.web_api_token}"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["file_count"] == 1
    mock_run_async.assert_called_once()


@patch("configstream.web._run_async_task")
def test_aggregate_requires_token(mock_run_async, settings, fs):
    """Ensure /api/aggregate enforces the configured API token."""
    client = _setup_test_client(settings)

    # Test without token
    response = client.post("/api/aggregate", json={})
    assert response.status_code == 401
    assert b"Missing or invalid API token" in response.data
    mock_run_async.assert_not_called()

    # Test with valid token
    mock_run_async.return_value = (Path("/secured"), [])
    response_ok = client.post(
        "/api/aggregate",
        json={},
        headers={"Authorization": f"Bearer {settings.security.web_api_token}"},
    )
    assert response_ok.status_code == 200
    mock_run_async.assert_called_once()


@patch("configstream.web._run_async_task")
def test_merge_route_success(mock_run_async, settings, fs):
    """Test the /api/merge route when the resume file exists."""
    client = _setup_test_client(settings)
    resume_file = Path(settings.output.output_dir) / "vpn_subscription_raw.txt"
    fs.create_file(resume_file, contents="test data")
    mock_run_async.return_value = None

    response = client.post(
        "/api/merge",
        json={},
        headers={"Authorization": f"Bearer {settings.security.web_api_token}"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "merge complete"
    mock_run_async.assert_called_once()


@patch("configstream.web._read_history", new_callable=AsyncMock)
def test_history_route_success(mock_read_history, settings, fs):
    """Test the /history route with successful data retrieval."""
    # Mount the real templates directory into the fake filesystem
    # This path is calculated relative to this test file.
    templates_path = Path(__file__).parent.parent / "src" / "configstream" / "templates"
    fs.add_real_directory(str(templates_path))

    client = _setup_test_client(settings)

    mock_read_history.return_value = {
        "proxy1": {
            "successes": 10,
            "failures": 0,
            "last_tested": 1672531200,
            "country": "US",
        },
    }

    response = client.get("/history")
    assert response.status_code == 200
    assert b"Complete Proxy History" in response.data
    assert b"proxy1" in response.data
    mock_read_history.assert_awaited_once()


# The following tests do not require special setup and can use the standard fixtures.
def test_index_route(client):
    """Test the index route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Dashboard - ConfigStream" in response.data


def test_health_check_route(client):
    """Test the /health route."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_sources_route(client, settings):
    """Test the /sources route."""
    Path(settings.sources.sources_file).write_text(
        "http://source1.com\nhttp://source2.com"
    )
    response = client.get("/sources")
    assert response.status_code == 200
    assert b"Subscription Sources" in response.data
    assert b"http://source1.com" in response.data


def test_analytics_route(client, settings):
    """Test the /analytics route."""
    db_path = Path(settings.output.output_dir) / settings.output.history_db_file
    db_path.touch()
    response = client.get("/analytics")
    assert response.status_code == 200
    assert b"Analytics - ConfigStream" in response.data


def test_settings_route(client, settings):
    """Test the /settings route."""
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"Application Settings" in response.data
    assert b"output_dir" in response.data
    assert settings.output.output_dir.name.encode() in response.data


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


def test_export_backup_api(client, settings):
    """Test the /api/export-backup endpoint."""
    response = client.get(
        "/api/export-backup",
        headers={"Authorization": f"Bearer {settings.security.web_api_token}"},
    )
    assert response.status_code == 200
    assert response.mimetype == "application/zip"

    zip_file = zipfile.ZipFile(io.BytesIO(response.data))
    assert "config.yaml" in zip_file.namelist()
    assert Path(settings.sources.sources_file).name in zip_file.namelist()


def test_import_backup_api_unauthorized(client, settings):
    """Test that the /api/import-backup endpoint requires authentication."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("config.yaml", "new_config_content")
    zip_buffer.seek(0)

    response = client.post(
        "/api/import-backup",
        data={"backup_file": (zip_buffer, "backup.zip")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 401


def test_import_backup_api(client, settings):
    """Test the /api/import-backup endpoint."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("config.yaml", "new_config_content")
    zip_buffer.seek(0)

    response = client.post(
        "/api/import-backup",
        data={"backup_file": (zip_buffer, "backup.zip")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {settings.security.web_api_token}"},
    )
    assert response.status_code == 200
    assert response.json["message"] == "Backup imported successfully."
    assert "new_config_content" in Path("config.yaml").read_text()