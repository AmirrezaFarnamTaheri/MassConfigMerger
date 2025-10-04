from __future__ import annotations

from massconfigmerger.clash_utils import build_clash_config, flag_emoji


def test_flag_emoji():
    """Test the flag_emoji function."""
    assert flag_emoji("US") == "🇺🇸"
    assert flag_emoji("jp") == "🇯🇵"
    assert flag_emoji(None) == "🏳"
    assert flag_emoji("") == "🏳"
    assert flag_emoji("USA") == "🏳"
    assert flag_emoji("U") == "🏳"


def test_build_clash_config():
    """Test the build_clash_config function."""
    # Test with a list of proxies
    proxies = [
        {"name": "Proxy-1", "type": "ss"},
        {"name": "Proxy-2", "type": "vmess"},
    ]
    config_yaml = build_clash_config(proxies)

    assert "proxies:" in config_yaml
    assert "Proxy-1" in config_yaml
    assert "Proxy-2" in config_yaml
    assert "proxy-groups:" in config_yaml
    assert "⚡ Auto-Select" in config_yaml
    assert "🔰 MANUAL" in config_yaml
    assert "rules:" in config_yaml
    assert "MATCH,🔰 MANUAL" in config_yaml

    # Test with an empty list of proxies
    empty_config_yaml = build_clash_config([])
    assert empty_config_yaml == ""