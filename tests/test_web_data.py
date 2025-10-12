import pytest
from pathlib import Path
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from configstream.web_dashboard import get_current_results, get_history, filter_nodes, export_csv, export_json

@pytest.fixture
def app():
    """Create a mock app instance for each test."""
    app = MagicMock()
    app.logger = MagicMock()
    return app

def test_get_current_results_file_not_found(app, tmp_path):
    """Test get_current_results when the file doesn't exist."""
    results = get_current_results(app, tmp_path)
    assert results["timestamp"] is None
    assert results["nodes"] == []

def test_get_history_file_not_found(app, tmp_path):
    """Test get_history when the file doesn't exist."""
    history = get_history(app, tmp_path)
    assert history == []

def test_filter_nodes_no_filters():
    """Test that filtering with no filters returns the original node list."""
    nodes = [{"id": 1}, {"id": 2}]
    filtered = filter_nodes(nodes, {})
    assert filtered == nodes

def test_export_csv_empty_nodes():
    """Test that exporting an empty list of nodes returns an empty string."""
    result = export_csv([])
    assert result == ""

def test_get_current_results_invalid_json(app, tmp_path: Path):
    """Test get_current_results with invalid JSON."""
    results_file = tmp_path / "current_results.json"
    results_file.write_text("invalid json")
    results = get_current_results(app, tmp_path)
    assert results["timestamp"] is None
    assert results["nodes"] == []

def test_get_history_invalid_json(app, tmp_path: Path):
    """Test get_history with invalid JSON."""
    history_file = tmp_path / "history.jsonl"
    history_file.write_text("invalid json\n")
    history = get_history(app, tmp_path)
    assert history == []

def test_filter_nodes(tmp_path: Path):
    """Test filtering nodes."""
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

def test_export_csv(tmp_path: Path):
    """Test exporting data as CSV."""
    nodes = [{"protocol": "vless", "ping_ms": 100}]
    csv_data = export_csv(nodes)
    assert csv_data.replace('\r\n', '\n') == "ping_ms,protocol\n100,vless\n"

def test_export_json(tmp_path: Path):
    """Test exporting data as JSON."""
    nodes = [{"protocol": "vless", "ping_ms": 100}]
    json_data = export_json(nodes)
    assert json.loads(json_data) == nodes