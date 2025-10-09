from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Imports needed for manual app creation, inspired by conftest.py
import pytest
from flask import testing
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from configstream.web import create_app

# Note: No need to import Settings or app fixtures, as we'll use them manually.
SRC_PATH = Path(__file__).resolve().parents[1] / "src"


def _setup_app(fs, settings):
    """Helper to replicate app setup from conftest.py."""
    fs.add_real_directory(str(Path(SRC_PATH, "configstream", "templates")))
    app = create_app(settings_override=settings)
    app.config.update({"TESTING": True})

    # Werkzeug version pinning from conftest
    def _get_werkzeug_version() -> str:
        return "3.0.3"

    original_get_version = testing._get_werkzeug_version
    testing._get_werkzeug_version = _get_werkzeug_version

    # Middleware setup from conftest
    app.wsgi_app = DispatcherMiddleware(
        app.wsgi_app, {"/metrics": make_wsgi_app()})

    # Return app and a cleanup function
    def cleanup():
        testing._get_werkzeug_version = original_get_version

    return app, cleanup


def test_aggregate_api(fs, settings):
    """Test the /api/aggregate route."""
    with patch(
        "configstream.web.run_aggregation_pipeline", new_callable=AsyncMock
    ) as mock_run_pipeline:
        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        mock_run_pipeline.return_value = (
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
        assert payload["output_dir"] == str(settings.output.output_dir)
        assert payload["file_count"] == 1
        mock_run_pipeline.assert_awaited_once()
        cleanup()


def test_aggregate_requires_token(fs, settings):
    """Ensure /api/aggregate enforces the configured API token."""
    with patch(
        "configstream.web.run_aggregation_pipeline", new_callable=AsyncMock
    ) as mock_run_pipeline:
        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        # Test without token
        response = client.post("/api/aggregate", json={})
        assert response.status_code == 401
        assert b"Missing or invalid API token" in response.data
        mock_run_pipeline.assert_not_awaited()

        # Test with valid token
        mock_run_pipeline.return_value = (Path("/secured"), [])
        response_ok = client.post(
            "/api/aggregate",
            json={},
            headers={"Authorization": f"Bearer {settings.security.web_api_token}"},
        )
        assert response_ok.status_code == 200
        mock_run_pipeline.assert_awaited_once()
        cleanup()


def test_merge_route_success(fs, settings):
    """Test the /api/merge route when the resume file exists."""
    with patch(
        "configstream.web.run_merger_pipeline", new_callable=AsyncMock
    ) as mock_run_merger:
        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        resume_file = Path(settings.output.output_dir) / \
            "vpn_subscription_raw.txt"
        resume_file.parent.mkdir(parents=True, exist_ok=True)
        resume_file.write_text("test data")

        response = client.post(
            "/api/merge",
            json={},
            headers={"Authorization": f"Bearer {settings.security.web_api_token}"},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "merge complete"
        assert payload["resume_file"].endswith("vpn_subscription_raw.txt")
        mock_run_merger.assert_awaited_once()
        cleanup()


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


def test_history_route_success(fs, settings):
    """Test the /history route with successful data retrieval."""
    with patch("configstream.web.Database") as MockDatabase:
        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        # Ensure the database file exists in the fake filesystem
        db_path = Path(settings.output.output_dir) / \
            settings.output.history_db_file
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()

        mock_db_instance = MockDatabase.return_value
        mock_db_instance.connect = AsyncMock()
        mock_db_instance.close = AsyncMock()
        mock_db_instance.get_proxy_history = AsyncMock(
            return_value={
                "proxy1": {
                    "successes": 10,
                    "failures": 0,
                    "last_tested": 1672531200,
                    "country": "US",
                },
            }
        )

        response = client.get("/history")
        assert response.status_code == 200
        assert b"Complete Proxy History" in response.data
        assert b"proxy1" in response.data
        assert b"100.00%" in response.data
        cleanup()


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
    db_path = Path(settings.output.output_dir) / \
        settings.output.history_db_file
    db_path.touch()
    response = client.get("/analytics")
    assert response.status_code == 200
    assert b"Analytics - ConfigStream" in response.data


def test_settings_route(client, settings):
    """Test the /settings route."""
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"Application Settings" in response.data
    # Check for key parts of the config, less sensitive to exact formatting.
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
