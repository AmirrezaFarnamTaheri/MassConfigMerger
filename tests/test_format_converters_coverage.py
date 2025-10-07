from __future__ import annotations

import logging
from unittest.mock import patch

from configstream.core.format_converters import FormatConverter


def test_generate_clash_proxies_exception_handling(caplog):
    """Test that _generate_clash_proxies handles exceptions gracefully."""
    # Arrange
    configs = ["invalid-config-that-will-cause-error"]
    caplog.set_level(logging.DEBUG)

    # Mock the parser to raise an exception
    with patch("configstream.core.format_converters.ProxyParser.config_to_clash_proxy") as mock_parse:
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