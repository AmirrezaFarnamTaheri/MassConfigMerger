import pytest
from configstream.core.parsers.tuic import TuicParser


def test_tuic_parser_get_identifier():
    """Test the get_identifier method for TuicParser."""
    # With UUID
    config_uuid = "tuic://uuid:password@example.com:443"
    parser_uuid = TuicParser(config_uuid, 0)
    assert parser_uuid.get_identifier() == "uuid"

    # With password only
    config_pass = "tuic://:password@example.com:443"
    parser_pass = TuicParser(config_pass, 0)
    assert parser_pass.get_identifier() == "password"

    # With query param password
    config_query = "tuic://user@example.com:443?password=pw"
    parser_query = TuicParser(config_query, 0)
    assert parser_query.get_identifier() == "pw"


def test_tuic_parser_congestion_control_alias():
    """Test that the 'congestion_control' alias is correctly parsed."""
    config = "tuic://uuid:pass@example.com:443?congestion_control=bbr"
    parser = TuicParser(config, 0)
    result = parser.parse()
    assert result["congestion-control"] == "bbr"


def test_tuic_parser_udp_relay_mode_alias():
    """Test that the 'udp_relay_mode' alias is correctly parsed."""
    config = "tuic://uuid:pass@example.com:443?udp_relay_mode=native"
    parser = TuicParser(config, 0)
    result = parser.parse()
    assert result["udp-relay-mode"] == "native"
