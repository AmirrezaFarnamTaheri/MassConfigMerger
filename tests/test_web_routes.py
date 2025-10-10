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



def test_index_route(client):
    """Test the index route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"ConfigStream Dashboard" in response.data


def test_api_current_with_filters(client, settings):
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

        response = client.get("/api/current?protocol=vless")
        assert response.status_code == 200
        mock_get_results.assert_called_once()
        mock_filter_nodes.assert_called_once_with(nodes, {"protocol": "vless"})


def test_api_statistics(client, settings):
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

        response = client.get("/api/statistics")
        assert response.status_code == 200
        stats = response.get_json()
        assert stats["total_nodes"] == 4
        assert stats["successful_nodes"] == 3
        assert stats["protocols"] == {"vless": 2, "ss": 1}
        assert stats["countries"] == {"US": 2, "DE": 1}
        assert round(stats["avg_ping_by_country"]["US"]) == 125


def test_get_current_results_file_not_found(settings):
    """Test get_current_results when the file doesn't exist."""
    dashboard_data = DashboardData(settings)
    dashboard_data.current_file = Path("/nonexistent/file.json")
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


def test_api_export_csv(settings):
    """Test exporting data as CSV."""
    mock_dashboard_data = DashboardData(settings)
    nodes = [{"protocol": "vless", "ping_time": 100}]
    mock_dashboard_data.get_current_results = lambda: {"nodes": nodes}
    mock_dashboard_data.filter_nodes = lambda nodes, filters: nodes
    mock_dashboard_data.export_csv = lambda nodes: "protocol,ping_time\nvless,100"

    app = create_app(settings=settings, dashboard_data=mock_dashboard_data)
    client = app.test_client()

    response = client.get("/api/export/csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.data == b"protocol,ping_time\nvless,100"


def test_api_export_json(settings):
    """Test exporting data as JSON."""
    mock_dashboard_data = DashboardData(settings)
    nodes = [{"protocol": "vless", "ping_time": 100}]
    mock_dashboard_data.get_current_results = lambda: {"nodes": nodes}
    mock_dashboard_data.filter_nodes = lambda nodes, filters: nodes
    mock_dashboard_data.export_json = lambda nodes: json.dumps(nodes)

    app = create_app(settings=settings, dashboard_data=mock_dashboard_data)
    client = app.test_client()

    response = client.get("/api/export/json")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.get_json() == nodes


def test_api_export_unsupported(client, settings):
    """Test exporting with an unsupported format."""
    response = client.get("/api/export/xml")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Unsupported format: xml"}


def test_dashboard_data_get_history(settings):
    """Test DashboardData.get_history method."""
    dashboard_data = DashboardData(settings)
    history_file = dashboard_data.history_file

    now = datetime.now()
    old_ts = (now - timedelta(hours=30)).isoformat()
    new_ts = (now - timedelta(hours=1)).isoformat()
    history_file.write_text(f'{{"timestamp": "{old_ts}"}}\n' f'{{"timestamp": "{new_ts}"}}\n')

    history = dashboard_data.get_history(hours=24)
    assert len(history) == 1
    assert history[0]["timestamp"] == new_ts