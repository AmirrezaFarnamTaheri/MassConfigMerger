from __future__ import annotations

import logging
from unittest.mock import patch
import textwrap

from configstream.core.format_converters import FormatConverter
from configstream.format_converters_extra import generate_surge_conf, generate_qx_conf


def test_generate_clash_proxies_exception_handling(caplog):
    """Test that _generate_clash_proxies handles exceptions gracefully."""
    # Arrange
    configs = ["invalid-config-that-will-cause-error"]
    caplog.set_level(logging.DEBUG)

    # Mock the parser to raise an exception
    with patch(
        "configstream.core.format_converters.ProxyParser.config_to_clash_proxy"
    ) as mock_parse:
        mock_parse.side_effect = Exception("Test parsing error")

        # Act
        converter = FormatConverter(configs)

        # Assert
        # Proxies list should be empty
        assert not converter.proxies
        # Check if the error was logged
        assert "Could not parse config for Clash" in caplog.text
        assert "Test parsing error" in caplog.text


def test_to_clash_config_no_proxies():
    """Test to_clash_config returns an empty string when there are no proxies."""
    # Arrange
    converter = FormatConverter([])

    # Act
    result = converter.to_clash_config()

    # Assert
    assert result == ""


def test_to_clash_proxies_no_proxies():
    """Test to_clash_proxies returns an empty string when there are no proxies."""
    # Arrange
    converter = FormatConverter([])

    # Act
    result = converter.to_clash_proxies()

    # Assert
    assert result == ""


def test_generate_surge_conf():
    proxies = [
        {
            "name": "ws",
            "type": "vmess",
            "server": "s.com",
            "port": 443,
            "uuid": "id",
            "tls": True,
            "network": "ws",
            "host": "h",
            "path": "/ws",
        },
        {
            "name": "grpc",
            "type": "vless",
            "server": "g.com",
            "port": 443,
            "uuid": "id2",
            "tls": True,
            "network": "grpc",
            "serviceName": "sn",
        },
    ]
    conf = generate_surge_conf(proxies)
    expected = textwrap.dedent(
        """
        [Proxy]
        ws = vmess, s.com, 443, username=id, tls=true, ws=true, ws-path=/ws, ws-headers=Host:h
        grpc = vless, g.com, 443, username=id2, tls=true, grpc=true, grpc-service-name=sn
        """
    ).strip()
    assert conf == expected


def test_generate_qx_conf():
    proxies = [
        {
            "name": "ws",
            "type": "vmess",
            "server": "s.com",
            "port": 443,
            "uuid": "id",
            "tls": True,
            "network": "ws",
            "host": "h",
            "path": "/ws",
        },
        {
            "name": "grpc",
            "type": "vless",
            "server": "g.com",
            "port": 443,
            "uuid": "id2",
            "tls": True,
            "network": "grpc",
            "serviceName": "sn",
        },
    ]
    conf = generate_qx_conf(proxies)
    expected = textwrap.dedent(
        """
        vmess=s.com:443, id=id, tls=true, obfs=ws, obfs-host=h, obfs-uri=/ws, tag=ws
        vless=g.com:443, id=id2, tls=true, obfs=grpc, grpc-service-name=sn, tag=grpc
        """
    ).strip()
    assert conf == expected


def test_generate_surge_conf_missing_optional():
    proxies = [
        {
            "name": "ws-only",
            "type": "vmess",
            "server": "s.com",
            "port": 443,
            "network": "ws",
        },
        {
            "name": "grpc-only",
            "type": "vless",
            "server": "g.com",
            "port": 443,
            "network": "grpc",
        },
        {
            "type": "ss",
            "server": "x.com",
            "port": 80,
            "cipher": "aes-128-gcm",
            "password": "pass",
        },
    ]
    conf = generate_surge_conf(proxies)
    expected = textwrap.dedent(
        """
        [Proxy]
        ws-only = vmess, s.com, 443, ws=true
        grpc-only = vless, g.com, 443, grpc=true
        proxy = ss, x.com, 80, encrypt-method=aes-128-gcm, password=pass
        """
    ).strip()
    assert conf == expected


def test_generate_qx_conf_missing_optional():
    proxies = [
        {
            "name": "ws-only",
            "type": "vmess",
            "server": "s.com",
            "port": 443,
            "network": "ws",
        },
        {
            "name": "grpc-only",
            "type": "vless",
            "server": "g.com",
            "port": 443,
            "network": "grpc",
        },
        {
            "type": "ss",
            "server": "x.com",
            "port": 80,
            "cipher": "aes-128-gcm",
            "password": "pass",
        },
    ]
    conf = generate_qx_conf(proxies)
    expected = textwrap.dedent(
        """
        vmess=s.com:443, obfs=ws, tag=ws-only
        vless=g.com:443, obfs=grpc, tag=grpc-only
        ss=x.com:80, password=pass, method=aes-128-gcm, tag=proxy
        """
    ).strip()
    assert conf == expected
