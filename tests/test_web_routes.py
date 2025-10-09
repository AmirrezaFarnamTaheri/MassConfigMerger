from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from flask import testing
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from configstream.config import Settings
from configstream.web import DashboardData, create_app
from configstream.web_utils import (
    _classify_reliability,
    _coerce_float,
    _coerce_int,
    _format_timestamp,
    _serialize_history,
)

SRC_PATH = Path(__file__).resolve().parents[1] / "src"


def _setup_app(fs, settings):
    """Helper to replicate app setup from conftest.py."""
    fs.add_real_directory(str(Path(SRC_PATH, "configstream", "templates")))
    app = create_app(settings_override=settings)
    app.config.update({"TESTING": True})

    def _get_werkzeug_version() -> str:
        return "3.0.3"

    original_get_version = testing._get_werkzeug_version
    testing._get_werkzeug_version = _get_werkzeug_version

    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})

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
        mock_run_pipeline.assert_awaited_once()
        cleanup()


def test_merge_route_success(fs, settings):
    """Test the /api/merge route when the resume file exists."""
    with patch(
        "configstream.web.run_merger_pipeline", new_callable=AsyncMock
    ) as mock_run_merger:
        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        resume_file = Path(settings.output.output_dir) / "vpn_subscription_raw.txt"
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
        mock_run_merger.assert_awaited_once()
        cleanup()


def test_index_route(client):
    """Test the index route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"ConfigStream Dashboard" in response.data


def test_health_check_route(client):
    """Test the /health route."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_api_current_with_filters(fs, settings):
    """Test the /api/current endpoint with filters."""
    with patch("configstream.web.DashboardData.get_current_results") as mock_get_results, patch(
        "configstream.web.DashboardData.filter_nodes"
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
    with patch("configstream.web.DashboardData.get_current_results") as mock_get_results:
        mock_get_results.return_value = {
            "nodes": [
                {"protocol": "vless", "country": "US", "ping_ms": 100},
                {"protocol": "vless", "country": "DE", "ping_ms": 200},
                {"protocol": "ss", "country": "US", "ping_ms": 150},
                {"protocol": "vless", "country": "US", "ping_ms": -1},
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
        assert stats["avg_ping_by_country"]["US"] == 125.0
        cleanup()


def test_get_current_results_file_not_found(fs):
    """Test get_current_results when the file doesn't exist."""
    data_dir = Path("/test_data")
    fs.create_dir(data_dir)
    settings = Settings(
        output={
            "current_results_file": data_dir / "results.json",
            "history_file": data_dir / "history.jsonl",
        }
    )
    dashboard_data = DashboardData(settings)
    results = dashboard_data.get_current_results()
    assert results == {"timestamp": None, "nodes": []}


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
    with patch("configstream.web.DashboardData") as mock_dashboard_data_cls:
        mock_dashboard_data_instance = mock_dashboard_data_cls.return_value
        nodes = [{"protocol": "vless", "ping_ms": 100}]
        mock_dashboard_data_instance.get_current_results.return_value = {"nodes": nodes}
        mock_dashboard_data_instance.filter_nodes.return_value = nodes
        mock_dashboard_data_instance.export_csv.return_value = "protocol,ping_ms\nvless,100"

        app, cleanup = _setup_app(fs, settings)
        client = app.test_client()

        response = client.get("/api/export/csv")
        assert response.status_code == 200
        assert response.mimetype == "text/csv"
        assert "attachment" in response.headers["Content-Disposition"]
        assert response.data == b"protocol,ping_ms\nvless,100"
        cleanup()


def test_api_export_json(fs, settings):
    """Test exporting data as JSON."""
    with patch("configstream.web.DashboardData") as mock_dashboard_data_cls:
        mock_dashboard_data_instance = mock_dashboard_data_cls.return_value
        nodes = [{"protocol": "vless", "ping_ms": 100}]
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
    assert response.get_json() == {"error": "Unsupported format"}
    cleanup()


def test_dashboard_data_get_history(fs):
    """Test DashboardData.get_history method."""
    data_dir = Path("/data")
    fs.create_dir(data_dir)
    settings = Settings(
        output={
            "current_results_file": data_dir / "results.json",
            "history_file": data_dir / "history.jsonl",
        }
    )
    history_file = settings.output.history_file
    now = datetime.now()
    old_ts = (now - timedelta(hours=30)).isoformat()
    new_ts = (now - timedelta(hours=1)).isoformat()
    history_file.write_text(f'{{"timestamp": "{old_ts}"}}\n' f'{{"timestamp": "{new_ts}"}}\n')

    dashboard_data = DashboardData(settings)
    history = dashboard_data.get_history(hours=24)
    assert len(history) == 1
    assert history[0]["timestamp"] == new_ts


def test_dashboard_data_filter_nodes():
    """Test DashboardData.filter_nodes with various filters."""
    dashboard_data = DashboardData(Settings())
    nodes = [
        {
            "protocol": "vless",
            "country": "US",
            "ping_ms": 100,
            "is_blocked": False,
            "city": "new york",
            "organization": "isp1",
            "ip": "1.1.1.1",
        },
        {
            "protocol": "ss",
            "country": "DE",
            "ping_ms": 200,
            "is_blocked": True,
            "city": "berlin",
            "organization": "isp2",
            "ip": "2.2.2.2",
        },
        {
            "protocol": "vless",
            "country": "US",
            "ping_ms": 50,
            "is_blocked": False,
            "city": "chicago",
            "organization": "isp3",
            "ip": "3.3.3.3",
        },
    ]

    # Test protocol filter
    filtered = dashboard_data.filter_nodes(nodes, {"protocol": "vless"})
    assert len(filtered) == 2
    assert all(n["protocol"] == "vless" for n in filtered)

    # Test country filter
    filtered = dashboard_data.filter_nodes(nodes, {"country": "DE"})
    assert len(filtered) == 1
    assert filtered[0]["country"] == "DE"

    # Test min ping filter
    filtered = dashboard_data.filter_nodes(nodes, {"min_ping": "75"})
    assert len(filtered) == 2
    assert all(n["ping_ms"] >= 75 for n in filtered)

    # Test max ping filter
    filtered = dashboard_data.filter_nodes(nodes, {"max_ping": "150"})
    assert len(filtered) == 2
    assert all(n["ping_ms"] <= 150 for n in filtered)

    # Test exclude blocked filter
    filtered = dashboard_data.filter_nodes(nodes, {"exclude_blocked": "true"})
    assert len(filtered) == 2
    assert all(not n["is_blocked"] for n in filtered)

    # Test search filter
    filtered = dashboard_data.filter_nodes(nodes, {"search": "york"})
    assert len(filtered) == 1
    assert filtered[0]["city"] == "new york"


def test_dashboard_data_export_json():
    """Test DashboardData.export_json method."""
    dashboard_data = DashboardData(Settings())
    nodes = [{"protocol": "vless", "ping_ms": 100}]
    json_output = dashboard_data.export_json(nodes)
    assert json.loads(json_output) == nodes


def test_helper_functions():
    """Test various helper functions in web_utils.py."""
    assert _coerce_int("10") == 10
    assert _coerce_int(None) == 0
    assert _coerce_int("abc") == 0

    assert _coerce_float("10.5") == 10.5
    assert _coerce_float(None) is None
    assert _coerce_float("abc") is None

    assert "1970-01-01 00:00:00" in _format_timestamp(0)
    assert _format_timestamp("abc") == "N/A"

    assert _classify_reliability(10, 0) == ("Healthy", "status-healthy")
    assert _classify_reliability(6, 4) == ("Warning", "status-warning")
    assert _classify_reliability(2, 8) == ("Critical", "status-critical")
    assert _classify_reliability(0, 0) == ("Untested", "status-untested")


def test_serialize_history():
    """Test the _serialize_history function."""
    history_data = {
        "proxy1": {
            "successes": 10,
            "failures": 0,
            "last_tested": 1672531200,
            "country": "US",
            "isp": "ISP A",
            "latency_ms": 50,
        },
        "proxy2": {
            "successes": 5,
            "failures": 5,
            "last_tested": 1672531200,
            "country": "DE",
            "isp": "ISP B",
            "latency": 150,
        },
    }
    serialized = _serialize_history(history_data)
    assert len(serialized) == 2
    assert serialized[0]["key"] == "proxy1"
    assert serialized[0]["reliability_percent"] == 100.0
    assert serialized[1]["key"] == "proxy2"
    assert serialized[1]["reliability_percent"] == 50.0


def test_api_sources_add_remove(fs, settings):
    """Test adding and removing sources via the API."""
    app, cleanup = _setup_app(fs, settings)
    client = app.test_client()

    sources_file = Path(settings.sources.sources_file)
    sources_file.touch()

    # Add a source
    response = client.post("/api/sources/add", json={"url": "http://source1.com"})
    assert response.status_code == 200
    assert "Source added successfully" in response.get_json()["message"]
    assert "http://source1.com" in sources_file.read_text()

    # Add same source again
    response = client.post("/api/sources/add", json={"url": "http://source1.com"})
    assert response.status_code == 200
    assert "Source already exists" in response.get_json()["message"]

    # Remove the source
    response = client.post("/api/sources/remove", json={"url": "http://source1.com"})
    assert response.status_code == 200
    assert "Source removed successfully" in response.get_json()["message"]
    assert "http://source1.com" not in sources_file.read_text()

    cleanup()