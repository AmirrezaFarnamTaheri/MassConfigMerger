import pytest
from massconfigmerger.core.parsers.hysteria import HysteriaParser

def test_hysteria_parser_username_as_password():
    """Test that username is used as password if password is not present."""
    config = "hysteria://user@example.com:443"
    parser = HysteriaParser(config, 0, "hysteria")
    result = parser.parse()
    assert result["password"] == "user"

def test_hysteria_parser_up_down_mbps():
    """Test parsing of upmbps and downmbps aliases."""
    config = "hysteria://user@example.com:443?up=10&down=50"
    parser = HysteriaParser(config, 0, "hysteria")
    result = parser.parse()
    assert result["upmbps"] == "10"
    assert result["downmbps"] == "50"

    config2 = "hysteria://user@example.com:443?up_mbps=20&down_mbps=60"
    parser2 = HysteriaParser(config2, 0, "hysteria")
    result2 = parser2.parse()
    assert result2["upmbps"] == "20"
    assert result2["downmbps"] == "60"

def test_hysteria_get_identifier():
    """Test the get_identifier method for HysteriaParser."""
    config = "hysteria://user:pass@example.com:443"
    parser = HysteriaParser(config, 0, "hysteria")
    assert parser.get_identifier() == "pass"

    config2 = "hysteria://user@example.com:443?password=pw"
    parser2 = HysteriaParser(config2, 0, "hysteria")
    assert parser2.get_identifier() == "pw"

    config3 = "hysteria://user@example.com:443"
    parser3 = HysteriaParser(config3, 0, "hysteria")
    assert parser3.get_identifier() == "user"