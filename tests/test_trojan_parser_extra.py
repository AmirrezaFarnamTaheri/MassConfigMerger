from __future__ import annotations

from configstream.core.parsers.trojan import TrojanParser


def test_parse_trojan_minimal_config():
    """Test parsing a minimal Trojan config link without optional query parameters."""
    config = "trojan://password@example.com:443#MinimalTrojan"

    parser = TrojanParser(config, 0)
    result = parser.parse()

    assert result is not None
    assert result["name"] == "MinimalTrojan"
    assert result["server"] == "example.com"
    assert result["port"] == 443
    assert result["password"] == "password"

    # Ensure optional fields are not present
    assert "sni" not in result
    assert "tls" not in result
    assert "network" not in result
    assert "host" not in result
    assert "path" not in result
    assert "alpn" not in result
    assert "flow" not in result
    assert "serviceName" not in result
    assert "ws-headers" not in result


def test_parse_trojan_full_config():
    """Test parsing a Trojan config with all optional query parameters."""
    config = (
        "trojan://password@example.com:443?sni=sni.host&security=tls&type=ws&mode=gun"
        "&host=ws.host&path=/path&alpn=h2&flow=xtls-rprx-vision&serviceName=my-service"
        "&ws-headers=eyJIb3N0IjogImV4YW1wbGUuY29tIn0"  # {"Host": "example.com"}
    )

    parser = TrojanParser(config, 1)
    result = parser.parse()

    assert result is not None
    assert result["sni"] == "sni.host"
    assert result["tls"] is True
    assert result["network"] == "ws"
    assert result["host"] == "ws.host"
    assert result["path"] == "/path"
    assert result["alpn"] == "h2"
    assert result["flow"] == "xtls-rprx-vision"
    assert result["serviceName"] == "my-service"
    assert result["ws-headers"] == {"Host": "example.com"}