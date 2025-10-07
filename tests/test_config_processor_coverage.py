from __future__ import annotations

import base64
import pytest
from configstream.config import Settings
from configstream.core import config_normalizer
from configstream.core.config_processor import ConfigProcessor, categorize_protocol


@pytest.fixture
def config_processor() -> ConfigProcessor:
    """Returns a ConfigProcessor instance with default settings."""
    return ConfigProcessor(Settings())


def test_categorize_protocol():
    """Test the categorize_protocol function."""
    assert categorize_protocol("vmess://...") == "VMess"
    assert categorize_protocol("vless://...") == "VLESS"
    assert categorize_protocol("ss://...") == "Shadowsocks"
    assert categorize_protocol("ssr://...") == "ShadowsocksR"
    assert categorize_protocol("trojan://...") == "Trojan"
    assert categorize_protocol("hy2://...") == "Hysteria2"
    assert categorize_protocol("hysteria2://...") == "Hysteria2"
    assert categorize_protocol("hysteria://...") == "Hysteria"
    assert categorize_protocol("tuic://...") == "TUIC"
    assert categorize_protocol("reality://...") == "Reality"
    assert categorize_protocol("naive://...") == "Naive"
    assert categorize_protocol("juicity://...") == "Juicity"
    assert categorize_protocol("wireguard://...") == "WireGuard"
    assert categorize_protocol("shadowtls://...") == "ShadowTLS"
    assert categorize_protocol("brook://...") == "Brook"
    assert categorize_protocol("unknown://...") == "Other"


def test_filter_configs():
    """Test the filter_configs method with various rules."""
    configs = {
        "vmess://config1",
        "vless://config2",
        "ss://config3",
        "trojan://config4",
    }

    # 1. Test with fetch rules (simple inclusion)
    settings_fetch = Settings()
    settings_fetch.filtering.fetch_protocols = ["VMess", "Shadowsocks"]
    processor_fetch = ConfigProcessor(settings_fetch)
    filtered_fetch = processor_fetch.filter_configs(configs, use_fetch_rules=True)
    assert filtered_fetch == {"vmess://config1", "ss://config3"}

    # Test case-insensitivity for fetch rules
    settings_fetch_case = Settings()
    settings_fetch_case.filtering.fetch_protocols = ["vmess", "shadowsocks"]
    processor_fetch_case = ConfigProcessor(settings_fetch_case)
    filtered_fetch_case = processor_fetch_case.filter_configs(configs, use_fetch_rules=True)
    assert filtered_fetch_case == {"vmess://config1", "ss://config3"}

    # Test empty fetch protocols (should return all)
    settings_fetch_empty = Settings()
    settings_fetch_empty.filtering.fetch_protocols = []
    processor_fetch_empty = ConfigProcessor(settings_fetch_empty)
    filtered_fetch_empty = processor_fetch_empty.filter_configs(configs, use_fetch_rules=True)
    assert filtered_fetch_empty == configs

    # 2. Test with merge rules (include/exclude)
    settings_merge = Settings()
    settings_merge.filtering.merge_include_protocols = {"VMESS", "VLESS"}
    settings_merge.filtering.merge_exclude_protocols = {"VLESS"}  # exclude should win
    processor_merge = ConfigProcessor(settings_merge)
    filtered_merge = processor_merge.filter_configs(configs, use_fetch_rules=False)
    assert filtered_merge == {"vmess://config1"}

    # Test with no merge rules (should return all)
    settings_merge_all = Settings()
    settings_merge_all.filtering.merge_include_protocols = set()
    settings_merge_all.filtering.merge_exclude_protocols = set()
    processor_merge_all = ConfigProcessor(settings_merge_all)
    filtered_merge_all = processor_merge_all.filter_configs(configs, use_fetch_rules=False)
    assert filtered_merge_all == configs


def test_apply_tuning(config_processor: ConfigProcessor):
    """Test the apply_tuning method."""
    # Test a standard URI that can be tuned
    link = "trojan://password@example.com:443?peer=test.com#tuned"
    tuned_link = config_processor.apply_tuning(link)
    assert "mux=8" in tuned_link
    assert "smux=4" in tuned_link

    # Test a vmess link, which should be skipped
    vmess_link = "vmess://ey..."
    tuned_vmess = config_processor.apply_tuning(vmess_link)
    assert tuned_vmess == vmess_link

    # Test a link without a scheme, which should be skipped
    no_scheme_link = "password@example.com:443"
    tuned_no_scheme = config_processor.apply_tuning(no_scheme_link)
    assert tuned_no_scheme == no_scheme_link

    # Test a link with no double slash, which should be skipped
    no_slash_link = "trojan:password@example.com:443"
    tuned_no_slash = config_processor.apply_tuning(no_slash_link)
    assert tuned_no_slash == no_slash_link


def test_extract_host_port():
    """Test the extract_host_port method for various protocols."""
    # VMess
    vmess_b64 = base64.b64encode(b'{"add": "vmess.com", "port": 100}').decode()
    assert config_normalizer.extract_host_port(f"vmess://{vmess_b64}") == ("vmess.com", 100)

    # VLESS
    vless_b64 = base64.b64encode(b'{"add": "vless.com", "port": 200}').decode()
    assert config_normalizer.extract_host_port(f"vless://{vless_b64}") == ("vless.com", 200)

    # SSR
    ssr_raw = "ssr.com:300:origin:aes-128-gcm:plain:cGFzcw=="
    ssr_b64 = base64.urlsafe_b64encode(ssr_raw.encode()).decode()
    assert config_normalizer.extract_host_port(f"ssr://{ssr_b64}") == ("ssr.com", 300)

    # SSR with invalid parts
    ssr_invalid_raw = "ssr.com"
    ssr_invalid_b64 = base64.urlsafe_b64encode(ssr_invalid_raw.encode()).decode()
    assert config_normalizer.extract_host_port(f"ssr://{ssr_invalid_b64}") == (None, None)

    # Trojan
    assert config_normalizer.extract_host_port("trojan://pass@trojan.com:400") == ("trojan.com", 400)

    # Regex fallback
    assert config_normalizer.extract_host_port("other://user@regex.com:500/path") == ("regex.com", 500)

    # Invalid
    assert config_normalizer.extract_host_port("invalid-link") == (None, None)


def test_create_semantic_hash():
    """Test the create_semantic_hash method for various protocols."""
    # VLESS link
    vless_link = "vless://d9bda552-3c67-4d7a-b1a8-2c8c1a7e8a9f@example.com:443?encryption=none&security=tls&type=ws&host=example.com&path=/#VLESS-Test"
    vless_hash = config_normalizer.create_semantic_hash(vless_link, 0)

    # Same VLESS link with different fragment should have the same hash
    vless_link_2 = "vless://d9bda552-3c67-4d7a-b1a8-2c8c1a7e8a9f@example.com:443?encryption=none&security=tls&type=ws&host=example.com&path=/#VLESS-Test-Different-Fragment"
    vless_hash_2 = config_normalizer.create_semantic_hash(vless_link_2, 0)
    assert vless_hash == vless_hash_2

    # VLESS with different UUID should have a different hash
    vless_link_3 = "vless://e9bda552-3c67-4d7a-b1a8-2c8c1a7e8a9f@example.com:443?encryption=none&security=tls&type=ws&host=example.com&path=/#VLESS-Test"
    vless_hash_3 = config_normalizer.create_semantic_hash(vless_link_3, 0)
    assert vless_hash != vless_hash_3

    # Trojan link
    trojan_link = "trojan://password@trojan.com:443#Trojan-Test"
    trojan_hash = config_normalizer.create_semantic_hash(trojan_link, 0)

    # Same Trojan with different fragment
    trojan_link_2 = "trojan://password@trojan.com:443#Trojan-Test-2"
    trojan_hash_2 = config_normalizer.create_semantic_hash(trojan_link_2, 0)
    assert trojan_hash == trojan_hash_2

    # SS link (base64 encoded user info)
    ss_b64 = base64.b64encode(b"aes-256-gcm:password").decode()
    ss_link = f"ss://{ss_b64}@ss.com:8888#SS-Test"
    ss_hash = config_normalizer.create_semantic_hash(ss_link, 0)

    # Same SS link with different fragment
    ss_link_2 = f"ss://{ss_b64}@ss.com:8888#SS-Test-2"
    ss_hash_2 = config_normalizer.create_semantic_hash(ss_link_2, 0)
    assert ss_hash == ss_hash_2

    # A config with no host/port should still produce a hash
    no_host_link = "vless://d9bda552-3c67-4d7a-b1a8-2c8c1a7e8a9f@:?path=/#NoHost"
    no_host_hash = config_normalizer.create_semantic_hash(no_host_link, 0)
    assert isinstance(no_host_hash, str)


from unittest.mock import AsyncMock, patch
import logging
import asyncio

from configstream.core.config_processor import ConfigResult


@pytest.mark.asyncio
async def test_filter_malicious_disabled(config_processor: ConfigProcessor):
    """Test that _filter_malicious returns all results if the check is disabled."""
    config_processor.settings.security.apivoid_api_key = None
    results = [ConfigResult(config="c1", protocol="p1", is_reachable=True, host="h1")]

    filtered = await config_processor._filter_malicious(results)

    assert filtered == results


@pytest.mark.asyncio
async def test_filter_malicious_dns_failure(config_processor: ConfigProcessor, caplog):
    """Test that _filter_malicious keeps a config if DNS resolution fails."""
    config_processor.settings.security.apivoid_api_key = "test-key"
    config_processor.tester.resolve_host = AsyncMock(side_effect=Exception("DNS Error"))
    results = [ConfigResult(config="c1", protocol="p1", is_reachable=True, host="h1")]

    with caplog.at_level(logging.DEBUG):
        filtered = await config_processor._filter_malicious(results)

    assert filtered == results
    assert "Failed to resolve host h1: DNS Error" in caplog.text


@pytest.mark.asyncio
async def test_filter_malicious_check_failure(config_processor: ConfigProcessor, caplog):
    """Test that _filter_malicious keeps a config if the blocklist check fails."""
    config_processor.settings.security.apivoid_api_key = "test-key"
    config_processor.tester.resolve_host = AsyncMock(return_value="1.2.3.4")
    config_processor.blocklist_checker.is_malicious = AsyncMock(side_effect=Exception("API Error"))
    results = [ConfigResult(config="c1", protocol="p1", is_reachable=True, host="h1")]

    with caplog.at_level(logging.DEBUG):
        filtered = await config_processor._filter_malicious(results)

    assert filtered == results
    assert "Blocklist check failed for 1.2.3.4: API Error" in caplog.text


@pytest.mark.asyncio
@patch("configstream.core.config_processor.tqdm_asyncio")
async def test_test_configs_worker_failure(mock_tqdm, config_processor: ConfigProcessor, caplog):
    """Test that test_configs handles exceptions within the worker."""
    async def gather_side_effect(*tasks, **kwargs):
        return await asyncio.gather(*tasks)

    mock_tqdm.gather = AsyncMock(side_effect=gather_side_effect)

    config_processor._test_config = AsyncMock(side_effect=Exception("Worker failed"))
    config_processor.tester.close = AsyncMock()
    config_processor.blocklist_checker.close = AsyncMock()

    configs = {"vless://config1"}

    with caplog.at_level(logging.DEBUG):
        results = await config_processor.test_configs(configs)

    assert results == []
    assert "test_configs worker failed for vless://config1: Worker failed" in caplog.text

    config_processor.tester.close.assert_awaited_once()
    config_processor.blocklist_checker.close.assert_awaited_once()