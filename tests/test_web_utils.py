import pytest
from datetime import datetime, timezone
from configstream.web_utils import (
    _coerce_int,
    _coerce_float,
    _format_timestamp,
    _classify_reliability,
    _serialize_history,
)

# Tests for _coerce_int
@pytest.mark.parametrize(
    "value, expected",
    [
        (123, 123),
        ("456", 456),
        (None, 0),
        ("", 0),
        ("abc", 0),
        (12.34, 12),
    ],
)
def test_coerce_int(value, expected):
    assert _coerce_int(value) == expected

# Tests for _coerce_float
@pytest.mark.parametrize(
    "value, expected",
    [
        (12.34, 12.34),
        ("56.78", 56.78),
        (None, None),
        ("", None),
        ("abc", None),
        (123, 123.0),
    ],
)
def test_coerce_float(value, expected):
    assert _coerce_float(value) == expected

# Tests for _format_timestamp
@pytest.mark.parametrize(
    "value, expected_pattern",
    [
        (datetime(2023, 1, 1).timestamp(), r"2023-01-01 00:00:00"),
        ("not-a-timestamp", "N/A"),
        (None, "N/A"),
        (9999999999999999999999, "N/A"), # Test overflow
    ],
)
def test_format_timestamp(value, expected_pattern):
    assert _format_timestamp(value) == expected_pattern

# Tests for _classify_reliability
@pytest.mark.parametrize(
    "successes, failures, expected",
    [
        (10, 0, ("Healthy", "status-healthy")),
        (8, 2, ("Healthy", "status-healthy")),
        (6, 4, ("Warning", "status-warning")),
        (4, 6, ("Critical", "status-critical")),
        (0, 10, ("Critical", "status-critical")),
        (0, 0, ("Untested", "status-untested")),
    ],
)
def test_classify_reliability(successes, failures, expected):
    assert _classify_reliability(successes, failures) == expected

# Tests for _serialize_history
def test_serialize_history_basic():
    history_data = {
        "node1": {
            "successes": 10,
            "failures": 2,
            "latency_ms": 120.5,
            "last_tested": datetime(2023, 1, 1).timestamp(),
            "country": "US",
            "isp": "Test ISP",
        }
    }
    result = _serialize_history(history_data)
    assert len(result) == 1
    entry = result[0]
    assert entry["key"] == "node1"
    assert entry["successes"] == 10
    assert entry["failures"] == 2
    assert entry["tests"] == 12
    assert entry["reliability_percent"] == 83.33
    assert entry["status"] == "Healthy"
    assert entry["latency"] == 120.50
    assert entry["last_tested"] == "2023-01-01 00:00:00"
    assert entry["country"] == "US"
    assert entry["isp"] == "Test ISP"

def test_serialize_history_empty():
    assert _serialize_history({}) == []

def test_serialize_history_sorting():
    history_data = {
        "node_bad": {"successes": 1, "failures": 9},
        "node_good": {"successes": 9, "failures": 1},
        "node_medium": {"successes": 5, "failures": 5},
    }
    result = _serialize_history(history_data)
    assert [item["key"] for item in result] == ["node_good", "node_medium", "node_bad"]

def test_serialize_history_missing_fields():
    history_data = {"node_missing": {}}
    result = _serialize_history(history_data)
    entry = result[0]
    assert entry["successes"] == 0
    assert entry["failures"] == 0
    assert entry["reliability_percent"] == 0.0
    assert entry["status"] == "Untested"
    assert entry["latency"] is None
    assert entry["last_tested"] == "N/A"
    assert entry["country"] is None
    assert entry["isp"] is None