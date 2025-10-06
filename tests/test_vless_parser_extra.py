from __future__ import annotations

import pytest

from massconfigmerger.core.parsers.vless import VlessParser


@pytest.mark.parametrize(
    "query_params, expected_key, expected_value",
    [
        # pbk aliases
        ({"pbk": ["test-pbk"]}, "public-key", "test-pbk"),
        ({"public-key": ["test-pbk"]}, "public-key", "test-pbk"),
        ({"publicKey": ["test-pbk"]}, "public-key", "test-pbk"),
        ({"public_key": ["test-pbk"]}, "public-key", "test-pbk"),
        ({"publickey": ["test-pbk"]}, "public-key", "test-pbk"),
        # sid aliases
        ({"sid": ["test-sid"]}, "short-id", "test-sid"),
        ({"short-id": ["test-sid"]}, "short-id", "test-sid"),
        ({"shortId": ["test-sid"]}, "short-id", "test-sid"),
        ({"short_id": ["test-sid"]}, "short-id", "test-sid"),
        ({"shortid": ["test-sid"]}, "short-id", "test-sid"),
        # spiderX aliases
        ({"spiderX": ["test-spider"]}, "spider-x", "test-spider"),
        ({"spider-x": ["test-spider"]}, "spider-x", "test-spider"),
        ({"spider_x": ["test-spider"]}, "spider-x", "test-spider"),
    ],
)
def test_parse_reality_opts_aliases(query_params, expected_key, expected_value):
    """Test that all aliases for reality options are correctly parsed."""
    parser = VlessParser("", 0)
    opts, _, _, _ = parser._parse_reality_opts(query_params)
    assert opts[expected_key] == expected_value


def test_parse_vless_empty_fragment():
    """Test parsing a VLESS config with an empty fragment uses the default name."""
    config = "vless://uuid@example.com:443#"
    parser = VlessParser(config, 123)
    result = parser.parse()
    assert result["name"] == "vless-123"


def test_parse_reality_empty_fragment():
    """Test parsing a Reality config with an empty fragment uses the default name."""
    config = "reality://uuid@example.com:443#"
    parser = VlessParser(config, 456)
    result = parser.parse()
    assert result["name"] == "reality-456"


def test_parse_vless_minimal_config():
    """Test parsing a minimal VLESS config link."""
    config = "vless://uuid@example.com:443#MinimalVLESS"
    parser = VlessParser(config, 0)
    result = parser.parse()

    assert result is not None
    assert result["name"] == "MinimalVLESS"
    assert result["uuid"] == "uuid"
    assert "tls" not in result
    assert "network" not in result


def test_parse_reality_minimal_config():
    """Test parsing a minimal Reality config link."""
    config = "reality://uuid@example.com:443#MinimalReality"
    parser = VlessParser(config, 0)
    result = parser.parse()

    assert result is not None
    assert result["name"] == "MinimalReality"
    assert result["uuid"] == "uuid"
    assert result["tls"] is True  # Should be implicitly true for reality
    assert "network" not in result


def test_parse_vless_with_mode_for_network():
    """Test that 'mode' can be used as an alias for 'type' for network."""
    config = "vless://uuid@example.com:443?mode=ws#VLESS-ws"
    parser = VlessParser(config, 0)
    result = parser.parse()
    assert result is not None
    assert result["network"] == "ws"


def test_parse_reality_with_mode_for_network():
    """Test that 'mode' can be used as an alias for 'type' for network in reality links."""
    config = "reality://uuid@example.com:443?mode=grpc#Reality-grpc"
    parser = VlessParser(config, 0)
    result = parser.parse()
    assert result is not None
    assert result["network"] == "grpc"


def test_parse_vless_all_params():
    """Test parsing a VLESS config with all possible parameters."""
    config = (
        "vless://uuid@example.com:443?security=tls&type=ws&host=host.com&path=/path"
        "&sni=sni.com&alpn=h2&fp=chrome&flow=xtls-rprx-vision&serviceName=my-service"
        "&ws-headers=Host:header.com#VLESS-Full"
    )
    parser = VlessParser(config, 0)
    result = parser.parse()
    assert result["tls"] is True
    assert result["network"] == "ws"
    assert result["host"] == "host.com"
    assert result["path"] == "/path"
    assert result["sni"] == "sni.com"
    assert result["alpn"] == "h2"
    assert result["fp"] == "chrome"
    assert result["flow"] == "xtls-rprx-vision"
    assert result["serviceName"] == "my-service"
    assert result["ws-headers"] == {"Host": "header.com"}


def test_parse_reality_all_params():
    """Test parsing a Reality config with all possible parameters."""
    config = (
        "reality://uuid@example.com:443?type=grpc&host=host.com&path=/path"
        "&sni=sni.com&alpn=h2&fp=chrome&flow=xtls-rprx-vision&serviceName=my-service"
        "&publicKey=pbk&shortId=sid&spiderX=spider"
        "&ws-headers=Host:header.com#Reality-Full"
    )
    parser = VlessParser(config, 0)
    result = parser.parse()
    assert result["tls"] is True
    assert result["network"] == "grpc"
    assert result["host"] == "host.com"
    assert result["path"] == "/path"
    assert result["sni"] == "sni.com"
    assert result["alpn"] == "h2"
    assert result["fp"] == "chrome"
    assert result["flow"] == "xtls-rprx-vision"
    assert result["serviceName"] == "my-service"
    assert result["pbk"] == "pbk"
    assert result["sid"] == "sid"
    assert result["spiderX"] == "spider"
    assert result["reality-opts"] == {
        "public-key": "pbk",
        "short-id": "sid",
        "spider-x": "spider",
    }
    assert result["ws-headers"] == {"Host": "header.com"}


def test_parse_vless_missing_parts():
    """Test parsing VLESS URLs with missing components."""
    # No user
    config_no_user = "vless://@example.com:443#NoUser"
    parser = VlessParser(config_no_user, 0)
    result_no_user = parser.parse()
    assert result_no_user["uuid"] == ""

    # No host
    config_no_host = "vless://uuid@:443#NoHost"
    parser = VlessParser(config_no_host, 0)
    result_no_host = parser.parse()
    assert result_no_host["server"] == ""

    # No port
    config_no_port = "vless://uuid@example.com#NoPort"
    parser = VlessParser(config_no_port, 0)
    result_no_port = parser.parse()
    assert result_no_port["port"] == 0


def test_parse_reality_missing_parts():
    """Test parsing Reality URLs with missing components."""
    # No user
    config_no_user = "reality://@example.com:443#NoUser"
    parser = VlessParser(config_no_user, 0)
    result_no_user = parser.parse()
    assert result_no_user["uuid"] == ""

    # No host
    config_no_host = "reality://uuid@:443#NoHost"
    parser = VlessParser(config_no_host, 0)
    result_no_host = parser.parse()
    assert result_no_host["server"] == ""

    # No port
    config_no_port = "reality://uuid@example.com#NoPort"
    parser = VlessParser(config_no_port, 0)
    result_no_port = parser.parse()
    assert result_no_port["port"] == 0