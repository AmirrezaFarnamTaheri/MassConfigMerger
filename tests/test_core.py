from __future__ import annotations

import base64

import pytest
import yaml

from configstream.models import Proxy
from configstream.output import (generate_base64_subscription,
                                 generate_clash_config)


@pytest.fixture
def working_proxies():
    """Fixture for a list of working Proxy objects."""
    p1 = Proxy(
        config="vmess://test1",
        protocol="vmess",
        remarks="vmess-proxy",
        address="1.1.1.1",
        port=1000,
        uuid="uuid1",
        is_working=True,
    )
    p2 = Proxy(
        config="vless://test2",
        protocol="vless",
        remarks="vless-proxy",
        address="2.2.2.2",
        port=2000,
        uuid="uuid2",
        is_working=True,
    )
    return [p1, p2]


@pytest.fixture
def all_proxies(working_proxies):
    """Fixture for a list of all proxies, including failed ones."""
    p3 = Proxy(config="trojan://test3", protocol="trojan", address="3.3.3.3", port=3000, is_working=False)
    return working_proxies + [p3]


def test_generate_base64_subscription(all_proxies):
    """Test Base64 subscription generation."""
    content = generate_base64_subscription(all_proxies)
    decoded_content = base64.b64decode(content).decode("utf-8")
    assert "vmess://test1" in decoded_content
    assert "vless://test2" in decoded_content
    assert "trojan://test3" not in decoded_content
    assert len(decoded_content.splitlines()) == 2


def test_generate_clash_config(all_proxies):
    """Test Clash config generation."""
    content = generate_clash_config(all_proxies)
    config = yaml.safe_load(content)

    assert len(config["proxies"]) == 2
    assert config["proxies"][0]["name"] == "vmess-proxy"
    assert config["proxies"][1]["name"] == "vless-proxy"
    assert "🚀 ConfigStream" in [g["name"] for g in config["proxy-groups"]]


def test_generate_empty_outputs():
    """Test that empty inputs produce empty but valid outputs."""
    assert generate_base64_subscription([]) == ""
    assert yaml.safe_load(generate_clash_config([]))["proxies"] == []