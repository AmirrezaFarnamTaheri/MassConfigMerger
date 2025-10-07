from __future__ import annotations
import base64
from unittest.mock import patch

import pytest

from configstream.core.utils import parse_configs_from_text

def test_parse_configs_from_text_oversized_b64():
    """Test that oversized base64 lines are skipped."""
    # Create a base64 string that is longer than the max size
    long_string = "a" * 5000
    b64_string = base64.urlsafe_b64encode(long_string.encode()).decode()
    text = f"some text\n{b64_string}\nmore text"

    with patch("configstream.core.utils.MAX_DECODE_SIZE", 4000):
        configs = parse_configs_from_text(text)
        assert len(configs) == 0

def test_parse_configs_from_text_invalid_b64():
    """Test that invalid base64 lines are skipped."""
    text = "some text\ninvalid-base64-string\nmore text"
    configs = parse_configs_from_text(text)
    assert len(configs) == 0