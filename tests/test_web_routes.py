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
from configstream.web_dashboard import DashboardData, create_app

SRC_PATH = Path(__file__).resolve().parents[1] / "src"


def _setup_app(fs, settings):
    """Helper to replicate app setup from conftest.py."""
    fs.add_real_directory(str(Path(SRC_PATH, "configstream", "templates")))
    app = create_app(settings=settings)
    app.config.update({"TESTING": True})

    def _get_werkzeug_version() -> str:
        return "3.0.3"

    original_get_version = testing._get_werkzeug_version
    testing._get_werkzeug_version = _get_werkzeug_version

    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})

    def cleanup():
        testing._get_werkzeug_version = original_get_version

    return app, cleanup


def test_index_route(client):
    """Test the index route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"ConfigStream Dashboard" in response.data


def test_api_current_with_filters(fs, settings):
    """Test the /api/current endpoint with filters."""
    with patch("configstream.web_dashboard.DashboardData.get_current_results") as mock_get_results, patch(
        "configstream.web_dashboard.DashboardData.filter_nodes"
    ) as mock_filter_nodes:
        nodes = [{"id": 1, "protocol": "vless"}]
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
    with patch("configstream.web_dashboard.DashboardData.get_current_results") as mock_get_results:
        mock_get_results.return_value = {
            "nodes": [
                {"protocol": "vless", "country": "US", "ping_time": 100},
                {"protocol": "vless", "country": "DE", "ping_time": 200},
                {"protocol": "ss", "country": "US", "ping_time": 150},
                {"protocol": "vless", "country": "US", "ping_time": -1},
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


def test_get_current_results_file_not_found(fs):
    """Test get_current_results when the file doesn't exist."""
    data_dir = Path("/test_data")
    data_dir.mkdir(exist_ok=True)
    settings = Settings()
    dashboard_data = DashboardData(settings)
    dashboard_data.data_dir = data_dir
    dashboard_data.current_file = data_dir / "current_results.json"
    results = dashboard_data.get_current_results()
    assert results == {"timestamp": None, "total_tested": 0, "successful": 0, "failed": 0, "nodes": []}


def test_filter_nodes_no_filters():
    """Test that filtering with no filters returns the original node list."""
    dashboard_data = DashboardData(Settings())
    nodes = [{"id": 1}, {"id": 2}]
    filtered = dashboard_data.filter_nodes(nodes, {})
    assert filtered == nodes


def test_export_csv_empty_nodes():
    """Test that exporting an empty list of nodes returns an empty string."""
    dashboard_data = DashboardData(Settings())
    result = dashboard_data.export_csv([])
    assert result == ""


def test_api_export_csv(fs, settings):
    """Test exporting data as CSV."""
    with patch("configstream.web_dashboard.DashboardData") as mock_dashboard_data_cls:
        mock_dashboard_data_instance = mock_dashboard_data_cls.return_value
        nodes = [{"protocol": "vless", "ping_time": 100}]
        mock_dashboard_data_instance.get_current_results.return_value = {"nodes": nodes}
        mock_dashboard_data_instance.filter_nodes.return_value = nodes
        mock_dashboard_data_instance.export_csv.return_value = "protocol,ping_time\nvless,100"

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
    with patch("configstream.web_dashboard.DashboardData") as mock_dashboard_data_cls:
        mock_dashboard_data_instance = mock_dashboard_data_cls.return_value
        nodes = [{"protocol": "vless", "ping_time": 100}]
        mock_dashboard_data_instance.get_current_results.return_value = {"nodes": nodes}
        mock_dashboard_data_instance.filter_nodes.return_value = nodes
        mock_dashboard_data_instance.export_json.return_value = json.dumps(nodes)

        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        response = client.get("/api/export/json")
        assert response.status_code == 200
        assert response.mimetype == "application/json"
        assert "attachment" in response.headers["Content-Disposition"]
        assert response.get_json() == nodes
        cleanup()


def test_api_export_unsupported(fs, settings):
    """Test exporting with an unsupported format."""
    app, cleanup = _setup_app(fs, settings)
    client = app.test_client()
    response = client.get("/api/export/xml")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Unsupported format: xml"}
    cleanup()


def test_dashboard_data_get_history(fs):
    """Test DashboardData.get_history method."""
    data_dir = Path("/data")
    data_dir.mkdir(exist_ok=True)
    settings = Settings()
    dashboard_data = DashboardData(settings)
    dashboard_data.data_dir = data_dir
    history_file = data_dir / "history.jsonl"
    dashboard_data.history_file = history_file

    now = datetime.now()
    old_ts = (now - timedelta(hours=30)).isoformat()
    new_ts = (now - timedelta(hours=1)).isoformat()
    history_file.write_text(f'{{"timestamp": "{old_ts}"}}\n' f'{{"timestamp": "{new_ts}"}}\n')

    history = dashboard_data.get_history(hours=24)
    assert len(history) == 1
    assert history[0]["timestamp"] == new_ts