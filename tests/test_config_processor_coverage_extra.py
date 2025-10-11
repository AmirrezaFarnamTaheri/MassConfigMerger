from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.config import Settings
from configstream.core.config_processor import ConfigProcessor, ConfigResult
from configstream.exceptions import NetworkError


@pytest.mark.asyncio
async def test_test_configs_filter_malicious_exception(fs):
    """Test that test_configs handles exceptions from _run_security_checks."""
    settings = Settings()
    processor = ConfigProcessor(settings)
    processor._run_security_checks = AsyncMock(side_effect=Exception("API error"))
    processor.tester.close = AsyncMock()
    processor.blocklist_checker.close = AsyncMock()

    with patch("configstream.core.config_processor.logging.debug") as mock_debug:
        results = await processor.test_configs(["vless://config"], {})
        assert results == []

        # We can't compare exception objects directly, so we check the call arguments
        # to ensure our expected log was made, even if other logs were made too.
        found_log = False
        for call in mock_debug.call_args_list:
            if (
                len(call.args) > 1
                and "An error occurred during config testing" in str(call.args[0])
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

    with patch("configstream.core.config_normalizer.extract_host_port", return_value=(None, None)):
        result = await processor._test_config("invalid-config", {})
        assert not result.is_reachable
        assert result.ping_time is None
        assert result.country is None

    await processor.tester.close()
