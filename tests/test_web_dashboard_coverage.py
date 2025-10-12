import pytest
from unittest.mock import patch, MagicMock
import json
from pathlib import Path

from configstream.web_dashboard import DashboardData, create_app


@pytest.fixture
def dashboard_data(tmp_path: Path) -> DashboardData:
    """Fixture for DashboardData."""
    return DashboardData(tmp_path)


def test_get_current_results_invalid_json(dashboard_data: DashboardData):
    """Test get_current_results with invalid JSON."""
    results_file = dashboard_data.data_dir / "current_results.json"
    results_file.write_text("invalid json")
    results = dashboard_data.get_current_results()
    assert results["timestamp"] is None
    assert results["nodes"] == []


def test_get_history_invalid_json(dashboard_data: DashboardData):
    """Test get_history with invalid JSON."""
    history_file = dashboard_data.data_dir / "history.jsonl"
    history_file.write_text("invalid json\n")
    history = dashboard_data.get_history()
    assert history == []


def test_filter_nodes(dashboard_data: DashboardData):
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
    filtered = dashboard_data.filter_nodes(nodes, filters)
    assert len(filtered) == 1
    assert filtered[0]["protocol"] == "VLESS"
