import pytest
from massconfigmerger.core.parsers.shadowsocks import ShadowsocksParser
from massconfigmerger.exceptions import ParserError

def test_shadowsocks_parser_userinfo_no_password():
    """Test that ss link with username but no password in userinfo raises ParserError."""
    config = "ss://YWVzLTI1Ni1nY20@example.com:443"  # base64 of "aes-256-gcm"
    parser = ShadowsocksParser(config, 0)
    with pytest.raises(ParserError):
        parser.parse()

def test_shadowsocks_parser_get_identifier_no_password():
    """Test get_identifier when no password can be found."""
    config = "ss://@example.com:443"
    parser = ShadowsocksParser(config, 0)
    assert parser.get_identifier() is None

def test_shadowsocks_parser_get_identifier_from_userinfo_no_password():
    """Test get_identifier with userinfo that doesn't contain a password."""
    config = "ss://YWVzLTI1Ni1nY20@example.com:443"  # base64 of "aes-256-gcm"
    parser = ShadowsocksParser(config, 0)
    assert parser.get_identifier() is None