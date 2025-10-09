import base64
import json

from configstream.core.parsers.common import BaseParser


def test_sanitize_str_non_string():
    """Test that sanitize_str returns non-string values as is."""
    assert BaseParser.sanitize_str(123) == 123
    assert BaseParser.sanitize_str(None) is None
    assert BaseParser.sanitize_str(["a", "b"]) == ["a", "b"]


def test_sanitize_headers_empty_input():
    """Test sanitize_headers with empty or None input."""
    assert BaseParser.sanitize_headers(None) is None
    assert BaseParser.sanitize_headers("") is None


def test_sanitize_headers_invalid_string():
    """Test sanitize_headers with a string that is not valid base64 or JSON."""
    invalid_string = "this-is-just-a-plain-string"
    assert BaseParser.sanitize_headers(invalid_string) == invalid_string


def test_sanitize_headers_plain_json_string():
    """Test sanitize_headers with a plain JSON string."""
    headers_dict = {"Host": "example.com", "User-Agent": "test-agent"}
    json_string = json.dumps(headers_dict)
    assert BaseParser.sanitize_headers(json_string) == headers_dict


def test_sanitize_headers_base64_encoded_json():
    """Test sanitize_headers with a base64-encoded JSON string."""
    headers_dict = {"Host": "example.com", "User-Agent": "test-agent"}
    json_string = json.dumps(headers_dict)
    b64_string = base64.urlsafe_b64encode(json_string.encode()).decode()
    assert BaseParser.sanitize_headers(b64_string) == headers_dict


def test_sanitize_headers_dict():
    """Test sanitize_headers with a dictionary input."""
    headers_dict = {"Host": "  example.com  \n", "User-Agent": "\r test-agent"}
    expected_dict = {"Host": "example.com", "User-Agent": "test-agent"}
    assert BaseParser.sanitize_headers(headers_dict) == expected_dict


def test_sanitize_headers_non_dict_after_decode():
    """Test sanitize_headers when base64 decodes to a non-dict JSON value."""
    json_string = json.dumps("not a dict")
    b64_string = base64.urlsafe_b64encode(json_string.encode()).decode()
    assert BaseParser.sanitize_headers(b64_string) == "not a dict"
