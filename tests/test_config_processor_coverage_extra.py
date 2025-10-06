from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.core.config_processor import ConfigProcessor, ConfigResult
from massconfigmerger.exceptions import NetworkError


@pytest.mark.asyncio
async def test_filter_malicious_unresolved_host(fs):
    """Test that _filter_malicious handles unresolved hosts gracefully."""
    settings = Settings()
    settings.security.apivoid_api_key = "test-key"
    processor = ConfigProcessor(settings)
    processor.tester.resolve_host = AsyncMock(return_value=None)

    results = [ConfigResult(config="c1", protocol="p1", is_reachable=True, host="unresolved.com")]
    filtered = await processor._filter_malicious(results)
    assert filtered == results  # Should not filter if host can't be resolved
    await processor.tester.close()


@pytest.mark.asyncio
async def test_test_configs_filter_malicious_exception(fs):
    """Test that test_configs handles exceptions from _filter_malicious."""
    settings = Settings()
    processor = ConfigProcessor(settings)
    processor._filter_malicious = AsyncMock(side_effect=Exception("API error"))
    processor.tester.close = AsyncMock()
    processor.blocklist_checker.close = AsyncMock()


    with patch("massconfigmerger.core.config_processor.logging.debug") as mock_debug:
        results = await processor.test_configs(["vless://config"], {})
        assert results == []

        # We can't compare exception objects directly, so we check the call arguments
        # to ensure our expected log was made, even if other logs were made too.
        found_log = False
        for call in mock_debug.call_args_list:
            if (
                len(call.args) == 2
                and call.args[0] == "An error occurred during config testing: %s"
                and isinstance(call.args[1], Exception)
                and str(call.args[1]) == "API error"
            ):
                found_log = True
                break
        assert found_log, "Expected log message for exception was not found"
    await processor.tester.close()


@pytest.mark.asyncio
async def test_test_config_no_host_port():
    """Test _test_config when the config has no host or port."""
    settings = Settings()
    processor = ConfigProcessor(settings)

    with patch("massconfigmerger.core.config_normalizer.extract_host_port", return_value=(None, None)):
        result = await processor._test_config("invalid-config", {})
        assert not result.is_reachable
        assert result.ping_time is None
        assert result.country is None

    await processor.tester.close()