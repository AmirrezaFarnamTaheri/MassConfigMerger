from __future__ import annotations

import pytest

from configstream.config import Settings
from configstream.core.config_processor import ConfigProcessor, ConfigResult
from configstream.core.utils import get_sort_key, haversine_distance


def test_filter_by_isp():
    """Test the _filter_by_isp method."""
    settings = Settings()
    processor = ConfigProcessor(settings)

    results = [
        ConfigResult(config="c1", protocol="p1", is_reachable=True, isp="Google"),
        ConfigResult(config="c2", protocol="p2", is_reachable=True, isp="Amazon"),
        ConfigResult(config="c3", protocol="p3", is_reachable=True, isp="DigitalOcean"),
        ConfigResult(config="c4", protocol="p4", is_reachable=True, isp=None),
    ]

    # Test include
    settings.filtering.include_isps = {"Google", "Amazon"}
    settings.filtering.exclude_isps = set()
    filtered = processor._filter_by_isp(results)
    assert {r.config for r in filtered} == {"c1", "c2"}

    # Test exclude
    settings.filtering.include_isps = set()
    settings.filtering.exclude_isps = {"DigitalOcean"}
    filtered = processor._filter_by_isp(results)
    assert {r.config for r in filtered} == {"c1", "c2", "c4"}

    # Test include and exclude
    settings.filtering.include_isps = {"Google", "Amazon"}
    settings.filtering.exclude_isps = {"Amazon"}
    filtered = processor._filter_by_isp(results)
    assert {r.config for r in filtered} == {"c1"}

    # Test case-insensitivity
    settings.filtering.include_isps = {"google"}
    settings.filtering.exclude_isps = set()
    filtered = processor._filter_by_isp(results)
    assert {r.config for r in filtered} == {"c1"}

    # Test no rules
    settings.filtering.include_isps = set()
    settings.filtering.exclude_isps = set()
    filtered = processor._filter_by_isp(results)
    assert len(filtered) == 4


def test_haversine_distance():
    """Test the haversine_distance function."""
    # Paris to New York
    lat1, lon1 = 48.8566, 2.3522
    lat2, lon2 = 40.7128, -74.0060
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    assert 5800 < distance < 5900  # Approximately 5837 km


def test_proximity_sorting():
    """Test the proximity sorting logic."""
    settings = Settings()
    settings.processing.sort_by = "proximity"
    settings.processing.proximity_latitude = 34.0522
    settings.processing.proximity_longitude = -118.2437

    results = [
        # Los Angeles (close)
        ConfigResult(config="c1", protocol="p1", is_reachable=True,
                     latitude=34.0522, longitude=-118.2437),
        # New York (far)
        ConfigResult(config="c2", protocol="p2", is_reachable=True,
                     latitude=40.7128, longitude=-74.0060),
        # No location data
        ConfigResult(config="c3", protocol="p3", is_reachable=True,
                     latitude=None, longitude=None),
    ]

    key_func = get_sort_key(settings)
    results.sort(key=key_func)
    assert [r.config for r in results] == ["c1", "c2", "c3"]


def test_proximity_sorting_no_location():
    """Test that proximity sorting raises an error if location is not provided."""
    settings = Settings()
    settings.processing.sort_by = "proximity"
    with pytest.raises(ValueError):
        get_sort_key(settings)
