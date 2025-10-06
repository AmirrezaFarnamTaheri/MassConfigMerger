from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.core.config_processor import ConfigProcessor, ConfigResult


@pytest.mark.asyncio
async def test_filter_malicious_dns_failure_coverage():
    """Test _filter_malicious when DNS resolution fails to improve coverage."""
    settings = Settings()
    settings.security.apivoid_api_key = "test-key"
    processor = ConfigProcessor(settings)
    processor.tester.resolve_host = AsyncMock(side_effect=Exception("DNS Error"))

    results = [ConfigResult(config="c1", protocol="p1", is_reachable=True, host="dns-fails.com")]
    filtered = await processor._filter_malicious(results)
    assert filtered == results
    await processor.tester.close()


@pytest.mark.asyncio
async def test_test_config_with_reliability_coverage():
    """Test _test_config with reliability data in history to improve coverage."""
    settings = Settings()
    processor = ConfigProcessor(settings)
    history = {"example.com:443": {"successes": 1, "failures": 1}}
    with patch("massconfigmerger.core.config_normalizer.extract_host_port", return_value=("example.com", 443)):
        result = await processor._test_config("vless://config", history)
    assert result.reliability == 0.5
    await processor.tester.close()


def test_filter_configs_exclude_coverage():
    """Test filtering with exclude rules to improve coverage."""
    settings = Settings()
    settings.filtering.merge_exclude_protocols = {"VMESS"}
    processor = ConfigProcessor(settings)
    configs = {"vmess://config1", "vless://config2"}
    filtered = processor.filter_configs(configs)
    assert filtered == {"vless://config2"}