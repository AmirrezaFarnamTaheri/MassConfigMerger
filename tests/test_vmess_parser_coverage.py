import pytest
from massconfigmerger.core.parsers.vmess import VmessParser
from massconfigmerger.exceptions import ParserError
import base64
import json

def test_vmess_parser_fallback_no_username():
    """Test the fallback vmess parser when there is no username."""
    config = "vmess://@example.com:443"
    parser = VmessParser(config, 0)
    result = parser.parse()
    assert result["uuid"] == ""

def test_vmess_parser_get_identifier_no_id():
    """Test get_identifier when the JSON has no 'id' or 'uuid'."""
    vmess_data = {"add": "example.com", "port": 443}
    encoded_data = base64.b64encode(json.dumps(vmess_data).encode()).decode()
    config = f"vmess://{encoded_data}"
    parser = VmessParser(config, 0)
    assert parser.get_identifier() is None

def test_vmess_parser_get_identifier_fallback_no_username():
    """Test get_identifier fallback when there is no username."""
    config = "vmess://:443"
    parser = VmessParser(config, 0)
    assert parser.get_identifier() == ""