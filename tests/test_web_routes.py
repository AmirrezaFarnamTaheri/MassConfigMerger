from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import testing
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from configstream.config import Settings
from configstream.web_dashboard import create_app

SRC_PATH = Path(__file__).resolve().parents[1] / "src"


def _setup_app(fs, settings):
    """Helper to replicate app setup from conftest.py."""
    fs.add_real_directory(str(Path(SRC_PATH, "configstream", "templates")))
    with patch("importlib.metadata.version", return_value="3.0.3"):
        app = create_app(settings=settings)
        app.config.update({"TESTING": True})
        app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})

    def cleanup():
        pass

    return app, cleanup


def test_index_route(client):
    """Test the index route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to ConfigStream" in response.data


def test_documentation_route(client):
    response = client.get("/documentation")
    assert response.status_code == 200
    assert b"Documentation" in response.data












def test_sources_route(client):
    response = client.get("/sources")
    assert response.status_code == 200
    assert b"Sources" in response.data


def test_system_route(client):
    """Test the system route."""
    response = client.get("/system")
    assert response.status_code == 200
    assert b"System Monitoring" in response.data


def test_api_current_with_filters(fs, settings):
    """Test the /api/current endpoint with filters."""
    with patch("configstream.web_dashboard.get_current_results") as mock_get_results, patch(
        "configstream.web_dashboard.filter_nodes"
    ) as mock_filter_nodes:
        nodes = [{"id": 1, "protocol": "vless", "ping_ms": 100}]
        mock_get_results.return_value = {
            "timestamp": datetime.now().isoformat(),
            "nodes": nodes,
        }
        mock_filter_nodes.return_value = nodes

        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        response = client.get("/api/current?protocol=vless")
        assert response.status_code == 200
        mock_get_results.assert_called_once()
        mock_filter_nodes.assert_called_once_with(nodes, {"protocol": "vless"})
        cleanup()


def test_api_statistics(fs, settings):
    """Test the /api/statistics endpoint."""
    with patch("configstream.web_dashboard.get_current_results") as mock_get_results:
        mock_get_results.return_value = {
            "nodes": [
                    {"protocol": "vless", "country_code": "US", "ping_ms": 100},
                    {"protocol": "vless", "country_code": "DE", "ping_ms": 200},
                    {"protocol": "ss", "country_code": "US", "ping_ms": 150},
                    {"protocol": "vless", "country_code": "US", "ping_ms": -1},
            ]
        }

        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        response = client.get("/api/statistics")
        assert response.status_code == 200
        stats = response.get_json()
        assert stats["total_nodes"] == 4
        assert stats["successful_nodes"] == 3
        assert stats["protocols"] == {"vless": 2, "ss": 1}
        assert stats["countries"] == {"US": 2, "DE": 1}
        assert round(stats["avg_ping_by_country"]["US"]) == 125
        cleanup()

def test_api_export_csv(fs, settings):
    """Test exporting data as CSV."""
    with patch("configstream.web_dashboard.get_current_results") as mock_get_results, \
         patch("configstream.web_dashboard.filter_nodes") as mock_filter_nodes, \
         patch("configstream.web_dashboard.export_csv") as mock_export_csv:
        nodes = [{"protocol": "vless", "ping_time": 100}]
        mock_get_results.return_value = {"nodes": nodes}
        mock_filter_nodes.return_value = nodes
        mock_export_csv.return_value = "protocol,ping_time\nvless,100"

        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        response = client.get("/api/export/csv")
        assert response.status_code == 200
        assert response.mimetype == "text/csv"
        assert "attachment" in response.headers["Content-Disposition"]
        assert response.data == b"protocol,ping_time\nvless,100"
        cleanup()


def test_api_export_json(fs, settings):
    """Test exporting data as JSON."""
    with patch("configstream.web_dashboard.get_current_results") as mock_get_results, \
         patch("configstream.web_dashboard.filter_nodes") as mock_filter_nodes:
        nodes = [{"protocol": "vless", "ping_ms": 100}]
        mock_get_results.return_value = {"nodes": nodes}
        mock_filter_nodes.return_value = nodes

        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        response = client.get("/api/export/json")
        assert response.status_code == 200
        assert response.mimetype == "application/json"
        assert "attachment" in response.headers["Content-Disposition"]
        response_data = response.get_json()
        assert response_data["count"] == len(nodes)
        assert response_data["nodes"] == nodes
        assert "exported_at" in response_data
        cleanup()


def test_api_export_unsupported(fs, settings):
    """Test exporting with an unsupported format."""
    app, cleanup = _setup_app(fs, settings)
    client = app.test_client()
    response = client.get("/api/export/xml")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Unsupported format: xml"}
    cleanup()
