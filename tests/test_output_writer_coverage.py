import pytest
from pathlib import Path
from unittest.mock import patch
from typing import List

from configstream.config import Settings
from configstream.output_writer import write_clash_proxies
from configstream.core.config_processor import ConfigResult


@pytest.fixture
def mock_results() -> List[ConfigResult]:
    """Fixture for mock ConfigResult objects."""
    return [
        ConfigResult(
            config="vless://test1",
            protocol="VLESS",
            host="example.com",
            port=443,
            ping_time=0.1,
            is_reachable=True,
            source_url="http://source.com/1",
            country="US",
        )
    ]


@pytest.fixture
def mock_settings_fs() -> Settings:
    """Fixture for a default Settings object with a fake output directory for pyfakefs tests."""
    settings = Settings()
    settings.output.output_dir = Path("/fake_output")
    return settings


@patch("configstream.output_writer.ProxyParser")
def test_write_clash_proxies_no_valid_proxies(
    MockProxyParser, tmp_path: Path, mock_results: List[ConfigResult]
):
    """Test write_clash_proxies when no configs can be converted."""
    mock_parser_instance = MockProxyParser.return_value
    mock_parser_instance.config_to_clash_proxy.return_value = None

    output_file = write_clash_proxies(mock_results, tmp_path)
    assert "proxies: []" in output_file.read_text()
    MockProxyParser.assert_called_once()
    mock_parser_instance.config_to_clash_proxy.assert_called_once()
