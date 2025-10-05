from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock

from massconfigmerger.config import Settings
from massconfigmerger.core.config_processor import ConfigProcessor


def test_filter_configs_no_rules():
    """Test filter_configs when no include/exclude rules are provided."""
    settings = Settings()
    settings.filtering.merge_include_protocols = set()
    settings.filtering.merge_exclude_protocols = set()

    processor = ConfigProcessor(settings)
    configs = {"vless://test1", "ss://test2"}

    filtered_configs = processor.filter_configs(configs, use_fetch_rules=False)

    assert filtered_configs == configs


@pytest.mark.asyncio
@patch("massconfigmerger.core.config_processor.ConfigProcessor._test_config")
async def test_test_configs_worker_failure(mock_test_config: AsyncMock):
    """Test that the test_configs method handles a failure in a worker."""
    mock_test_config.side_effect = Exception("Test worker failure")
    settings = Settings()
    processor = ConfigProcessor(settings)

    configs = {"vless://test1"}

    # This should not raise an exception
    results = await processor.test_configs(configs)

    assert not results # The result from the failed worker should be excluded
    mock_test_config.assert_awaited_once_with("vless://test1")


@pytest.mark.asyncio
async def test_test_connection_wrapper():
    """Test the test_connection wrapper method."""
    settings = Settings()
    processor = ConfigProcessor(settings)

    with patch.object(processor.tester, "test_connection", new_callable=AsyncMock) as mock_test:
        mock_test.return_value = 0.123
        result = await processor.test_connection("example.com", 443)
        mock_test.assert_awaited_once_with("example.com", 443)
        assert result == 0.123


@pytest.mark.asyncio
async def test_lookup_country_wrapper():
    """Test the lookup_country wrapper method."""
    settings = Settings()
    processor = ConfigProcessor(settings)

    with patch.object(processor.tester, "lookup_country", new_callable=AsyncMock) as mock_lookup:
        mock_lookup.return_value = "US"
        result = await processor.lookup_country("example.com")
        mock_lookup.assert_awaited_once_with("example.com")
        assert result == "US"


def test_apply_tuning_wrapper():
    """Test the apply_tuning wrapper method."""
    settings = Settings()
    processor = ConfigProcessor(settings)
    config = "vless://test"

    with patch("massconfigmerger.core.config_processor.config_normalizer.apply_tuning") as mock_apply:
        mock_apply.return_value = "tuned-config"
        result = processor.apply_tuning(config)
        mock_apply.assert_called_once_with(config, settings)
        assert result == "tuned-config"