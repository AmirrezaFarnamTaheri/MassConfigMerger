from __future__ import annotations

import base64
import pytest
from massconfigmerger.config import Settings
from massconfigmerger.core import config_normalizer
from massconfigmerger.core.config_processor import ConfigProcessor


@pytest.fixture
def config_processor() -> ConfigProcessor:
    """Returns a ConfigProcessor instance with default settings."""
    return ConfigProcessor(Settings())


def test_categorize_protocol(config_processor: ConfigProcessor):
    """Test the categorize_protocol method."""
    assert config_processor.categorize_protocol("vmess://...") == "VMess"
    assert config_processor.categorize_protocol("vless://...") == "VLESS"
    assert config_processor.categorize_protocol("ss://...") == "Shadowsocks"
    assert config_processor.categorize_protocol("ssr://...") == "ShadowsocksR"
    assert config_processor.categorize_protocol("trojan://...") == "Trojan"
    assert config_processor.categorize_protocol("hy2://...") == "Hysteria2"
    assert config_processor.categorize_protocol("hysteria2://...") == "Hysteria2"
    assert config_processor.categorize_protocol("hysteria://...") == "Hysteria"
    assert config_processor.categorize_protocol("tuic://...") == "TUIC"
    assert config_processor.categorize_protocol("reality://...") == "Reality"
    assert config_processor.categorize_protocol("naive://...") == "Naive"
    assert config_processor.categorize_protocol("juicity://...") == "Juicity"
    assert config_processor.categorize_protocol("wireguard://...") == "WireGuard"
    assert config_processor.categorize_protocol("shadowtls://...") == "ShadowTLS"
    assert config_processor.categorize_protocol("brook://...") == "Brook"
    assert config_processor.categorize_protocol("unknown://...") == "Other"


def test_filter_configs(config_processor: ConfigProcessor):
    """Test the filter_configs method."""
    configs = {
        "vmess://config1",
        "vless://config2",
        "ss://config3",
        "trojan://config4",
    }

    # Test filtering for a subset of protocols
    filtered = config_processor.filter_configs(configs, protocols=["VMess", "Shadowsocks"])
    assert filtered == {"vmess://config1", "ss://config3"}

    # Test filtering with no protocol filter (should return all)
    filtered_all = config_processor.filter_configs(configs)
    assert filtered_all == configs

    # Test with case-insensitivity
    filtered_case = config_processor.filter_configs(configs, protocols=["vmess", "shadowsocks"])
    assert filtered_case == {"vmess://config1", "ss://config3"}

    # Test with an empty protocol list (should return all)
    filtered_empty = config_processor.filter_configs(configs, protocols=[])
    assert filtered_empty == configs


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
    vless_hash = config_normalizer.create_semantic_hash(vless_link)

    # Same VLESS link with different fragment should have the same hash
    vless_link_2 = "vless://d9bda552-3c67-4d7a-b1a8-2c8c1a7e8a9f@example.com:443?encryption=none&security=tls&type=ws&host=example.com&path=/#VLESS-Test-Different-Fragment"
    vless_hash_2 = config_normalizer.create_semantic_hash(vless_link_2)
    assert vless_hash == vless_hash_2

    # VLESS with different UUID should have a different hash
    vless_link_3 = "vless://e9bda552-3c67-4d7a-b1a8-2c8c1a7e8a9f@example.com:443?encryption=none&security=tls&type=ws&host=example.com&path=/#VLESS-Test"
    vless_hash_3 = config_normalizer.create_semantic_hash(vless_link_3)
    assert vless_hash != vless_hash_3

    # Trojan link
    trojan_link = "trojan://password@trojan.com:443#Trojan-Test"
    trojan_hash = config_normalizer.create_semantic_hash(trojan_link)

    # Same Trojan with different fragment
    trojan_link_2 = "trojan://password@trojan.com:443#Trojan-Test-2"
    trojan_hash_2 = config_normalizer.create_semantic_hash(trojan_link_2)
    assert trojan_hash == trojan_hash_2

    # SS link (base64 encoded user info)
    ss_b64 = base64.b64encode(b"aes-256-gcm:password").decode()
    ss_link = f"ss://{ss_b64}@ss.com:8888#SS-Test"
    ss_hash = config_normalizer.create_semantic_hash(ss_link)

    # Same SS link with different fragment
    ss_link_2 = f"ss://{ss_b64}@ss.com:8888#SS-Test-2"
    ss_hash_2 = config_normalizer.create_semantic_hash(ss_link_2)
    assert ss_hash == ss_hash_2

    # A config with no host/port should still produce a hash
    no_host_link = "vless://d9bda552-3c67-4d7a-b1a8-2c8c1a7e8a9f@:?path=/#NoHost"
    no_host_hash = config_normalizer.create_semantic_hash(no_host_link)
    assert isinstance(no_host_hash, str)