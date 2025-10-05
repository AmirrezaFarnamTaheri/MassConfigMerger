from __future__ import annotations

import pytest
from massconfigmerger.core.parsers.vless import parse, parse_reality, _parse_reality_opts


@pytest.mark.parametrize(
    "query_params, expected_key, expected_value",
    [
        ({"public-key": ["test-pbk"]}, "public-key", "test-pbk"),
        ({"publicKey": ["test-pbk"]}, "public-key", "test-pbk"),
        ({"short-id": ["test-sid"]}, "short-id", "test-sid"),
        ({"shortId": ["test-sid"]}, "short-id", "test-sid"),
        ({"spider-x": ["test-spider"]}, "spider-x", "test-spider"),
        ({"spider_x": ["test-spider"]}, "spider-x", "test-spider"),
    ],
)
def test_parse_reality_opts_aliases(query_params, expected_key, expected_value):
    """Test that all aliases for reality options are correctly parsed."""
    opts, _, _, _ = _parse_reality_opts(query_params)
    assert opts[expected_key] == expected_value


def test_parse_vless_minimal_config():
    """Test parsing a minimal VLESS config link."""
    config = "vless://uuid@example.com:443#MinimalVLESS"
    result = parse(config, 0)

    assert result is not None
    assert result["name"] == "MinimalVLESS"
    assert result["uuid"] == "uuid"
    assert "tls" not in result
    assert "network" not in result


def test_parse_reality_minimal_config():
    """Test parsing a minimal Reality config link."""
    config = "reality://uuid@example.com:443#MinimalReality"
    result = parse_reality(config, 0)

    assert result is not None
    assert result["name"] == "MinimalReality"
    assert result["uuid"] == "uuid"
    assert result["tls"] is True  # Should be implicitly true for reality
    assert "network" not in result


def test_parse_vless_with_mode_for_network():
    """Test that 'mode' can be used as an alias for 'type' for network."""
    config = "vless://uuid@example.com:443?mode=ws#VLESS-ws"
    result = parse(config, 0)
    assert result is not None
    assert result["network"] == "ws"


def test_parse_reality_with_mode_for_network():
    """Test that 'mode' can be used as an alias for 'type' for network in reality links."""
    config = "reality://uuid@example.com:443?mode=grpc#Reality-grpc"
    result = parse_reality(config, 0)
    assert result is not None
    assert result["network"] == "grpc"