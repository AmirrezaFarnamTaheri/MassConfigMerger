import base64
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from configstream.web_dashboard import (
    export_base64,
    export_csv,
    export_json,
    export_raw,
    filter_nodes,
    get_current_results,
    get_history,
)


@pytest.fixture
def app():
    """Create a mock app instance for each test."""
    app = MagicMock()
    app.logger = MagicMock()
    return app


def test_get_current_results_file_not_found(app, tmp_path: Path):
    """Return defaults when the results file is missing."""
    results = get_current_results(tmp_path, app.logger)
    assert results["timestamp"] is None
    assert results["nodes"] == []


def test_get_history_file_not_found(app, tmp_path: Path):
    """Return an empty list when the history file is missing."""
    history = get_history(tmp_path, 24, app.logger)
    assert history == []


def test_filter_nodes_no_filters():
    """Filtering with no criteria preserves all nodes and normalizes them."""
    nodes = [{"id": 1}, {"id": 2}]
    filtered = filter_nodes(nodes, {})
    assert len(filtered) == len(nodes)
    assert filtered[0]["country"] == "Unknown"


def test_export_csv_empty_nodes():
    """Exporting an empty list produces an empty payload."""
    result = export_csv([])
    assert result == ""


def test_get_current_results_invalid_json(app, tmp_path: Path):
    """Gracefully handle invalid JSON in the results file."""
    results_file = tmp_path / "current_results.json"
    results_file.write_text("invalid json")
    results = get_current_results(tmp_path, app.logger)
    assert results["timestamp"] is None
    assert results["nodes"] == []


def test_get_current_results_normalizes_nodes(app, tmp_path: Path):
    """Ensure nodes are normalized and unexpected keys trigger warnings."""
    results_file = tmp_path / "current_results.json"
    results_file.write_text(json.dumps({
        "timestamp": "2024-01-01T00:00:00Z",
        "nodes": [
            {"protocol": "vless", "ping_ms": "120", "country_code": "US"},
            "invalid-node",
        ],
        "unexpected": True,
    }))

    results = get_current_results(tmp_path, app.logger)
    assert results["nodes"][0]["country"] == "US"
    assert results["nodes"][0]["country_code"] == "US"
    assert results["total_tested"] == 1
    app.logger.warning.assert_called()


def test_get_history_invalid_json(app, tmp_path: Path):
    """Ignore malformed lines in the history file."""
    history_file = tmp_path / "history.jsonl"
    history_file.write_text("invalid json\n")
    history = get_history(tmp_path, 24, app.logger)
    assert history == []


def test_get_history_naive_timestamps(app, tmp_path: Path):
    """Handle naive timestamps by assuming the local timezone."""
    history_file = tmp_path / "history.jsonl"
    naive_timestamp = datetime.now().isoformat()
    history_file.write_text(json.dumps({"timestamp": naive_timestamp}) + "\n")
    history = get_history(tmp_path, 1, app.logger)
    assert len(history) == 1


def test_filter_nodes(tmp_path: Path):
    """Filter using protocol, country, ping bounds, and search."""
    nodes = [
        {"protocol": "VLESS", "country": "US", "ping_ms": 100, "is_blocked": False, "city": "New York", "organization": "Test", "ip": "1.1.1.1"},
        {"protocol": "SS", "country": "DE", "ping_ms": 200, "is_blocked": True, "city": "Berlin", "organization": "Test", "ip": "2.2.2.2"},
    ]
    filters = {
        "protocol": "VLESS",
        "country": "US",
        "min_ping": "50",
        "max_ping": "150",
        "exclude_blocked": "1",
        "search": "New",
    }
    filtered = filter_nodes(nodes, filters)
    assert len(filtered) == 1
    assert filtered[0]["protocol"] == "VLESS"


def test_filter_nodes_handles_missing_keys():
    """Missing keys should not break filtering."""
    nodes = [
        {"protocol": "VLESS", "ping_ms": "150", "config": "vless://example"},
        {"protocol": None, "ping_ms": None},
    ]
    filters = {"country": "US", "max_ping": "200"}
    filtered = filter_nodes(nodes, filters)
    assert isinstance(filtered, list)


def test_export_csv(tmp_path: Path):
    """Export nodes to CSV."""
    nodes = [{"protocol": "vless", "ping_ms": 100}]
    csv_data = export_csv(nodes)
    assert csv_data.replace('\r\n', '\n') == "ping_ms,protocol\n100,vless\n"


def test_export_json(tmp_path: Path):
    """Export nodes to JSON."""
    nodes = [{"protocol": "vless", "ping_ms": 100}]
    json_data = export_json(nodes)
    assert json.loads(json_data) == nodes


def test_export_raw(tmp_path: Path):
    """Export nodes to raw newline separated configs."""
    nodes = [{"config": "vless://example"}, {"config": "  "}]
    raw_data = export_raw(nodes)
    assert raw_data == "vless://example"


def test_export_base64(tmp_path: Path):
    """Export nodes to base64 payloads."""
    nodes = [{"config": "vless://example"}]
    encoded = export_base64(nodes)
    assert encoded == base64.b64encode("vless://example".encode("utf-8")).decode("utf-8")
