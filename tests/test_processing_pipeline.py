from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.core.config_processor import ConfigResult
from massconfigmerger.db import Database
from massconfigmerger.processing import pipeline


@pytest.mark.asyncio
async def test_update_proxy_history():
    """Test the update_proxy_history function."""
    mock_db = MagicMock(spec=Database)
    mock_db.update_proxy_history = AsyncMock()

    results = [
        ConfigResult(config="c1", protocol="p1", is_reachable=True, host="h1", port=1),
        ConfigResult(config="c2", protocol="p2", is_reachable=False, host="h2", port=2),
        ConfigResult(
            config="c3", protocol="p3", is_reachable=True, host=None, port=None
        ),  # Should be skipped
    ]

    await pipeline.update_proxy_history(mock_db, results)

    assert mock_db.update_proxy_history.call_count == 2
    mock_db.update_proxy_history.assert_any_await("h1:1", True)
    mock_db.update_proxy_history.assert_any_await("h2:2", False)


def test_sort_and_trim_results():
    """Test the sort_and_trim_results function."""
    results = [
        ConfigResult(config="c1", protocol="p1", ping_time=0.3, is_reachable=True),
        ConfigResult(config="c2", protocol="p2", ping_time=0.1, is_reachable=True),
        ConfigResult(config="c3", protocol="p3", ping_time=0.2, is_reachable=True),
        ConfigResult(config="c4", protocol="p4", ping_time=0.05, is_reachable=False),
    ]
    settings = Settings()

    # Test sorting by latency
    settings.processing.enable_sorting = True
    settings.processing.sort_by = "latency"
    sorted_results = pipeline.sort_and_trim_results(results.copy(), settings)
    assert [r.config for r in sorted_results] == ["c2", "c3", "c1", "c4"]

    # Test sorting by reliability
    results_reliability = [
        ConfigResult(config="c1", protocol="p1", reliability=0.9, is_reachable=True),
        ConfigResult(config="c2", protocol="p2", reliability=0.5, is_reachable=True),
        ConfigResult(config="c3", protocol="p3", reliability=1.0, is_reachable=True),
        ConfigResult(config="c4", protocol="p4", reliability=1.0, is_reachable=False),
    ]
    settings.processing.sort_by = "reliability"
    sorted_reliability = pipeline.sort_and_trim_results(results_reliability.copy(), settings)
    assert [r.config for r in sorted_reliability] == ["c3", "c1", "c2", "c4"]

    # Test trimming
    settings.processing.top_n = 2
    settings.processing.sort_by = "latency"
    trimmed_results = pipeline.sort_and_trim_results(results.copy(), settings)
    assert len(trimmed_results) == 2
    assert [r.config for r in trimmed_results] == ["c2", "c3"]

    # Test disabled sorting
    settings.processing.enable_sorting = False
    settings.processing.top_n = 0
    not_sorted_results = pipeline.sort_and_trim_results(results.copy(), settings)
    assert [r.config for r in not_sorted_results] == ["c1", "c2", "c3", "c4"]


@pytest.mark.asyncio
@patch("massconfigmerger.processing.pipeline.ConfigProcessor", new_callable=MagicMock)
async def test_test_configs(MockConfigProcessor):
    """Test the test_configs function."""
    mock_proc_instance = MockConfigProcessor.return_value
    mock_proc_instance.test_configs = AsyncMock(return_value=[])
    mock_proc_instance.tester.close = AsyncMock()

    settings = Settings()
    await pipeline.test_configs(["c1", "c2"], settings, {})

    mock_proc_instance.test_configs.assert_awaited_once_with(["c1", "c2"], {})
    mock_proc_instance.tester.close.assert_awaited_once()


def test_filter_results_by_ping():
    """Test the filter_results_by_ping function."""
    results = [
        ConfigResult(config="c1", protocol="p1", ping_time=0.1, is_reachable=True),  # 100ms
        ConfigResult(config="c2", protocol="p2", ping_time=0.3, is_reachable=True),  # 300ms
        ConfigResult(config="c3", protocol="p3", ping_time=None, is_reachable=False),
    ]
    settings = Settings()

    # Test with a limit
    settings.filtering.max_ping_ms = 200
    filtered = pipeline.filter_results_by_ping(results, settings)
    assert len(filtered) == 1
    assert filtered[0].config == "c1"

    # Test with no limit (should return all)
    settings.filtering.max_ping_ms = None
    filtered = pipeline.filter_results_by_ping(results, settings)
    assert len(filtered) == 3