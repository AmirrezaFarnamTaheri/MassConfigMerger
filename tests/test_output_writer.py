from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from configstream.config import Settings
from configstream.core.config_processor import ConfigResult
from configstream.output_writer import (
    write_base64_configs,
    write_clash_proxies,
    write_csv_report,
    write_raw_configs,
)
from configstream.report_generator import generate_html_report


@pytest.fixture
def sample_results() -> list[ConfigResult]:
    """Return a sample list of ConfigResult objects for testing."""
    return [
        ConfigResult(
            config="vmess://config1",
            protocol="VMess",
            host="example.com",
            port=443,
            ping_time=0.123,
            is_reachable=True,
            country="US",
        )
    ]


def test_write_raw_configs(fs, sample_results: list[ConfigResult]):
    fs.create_dir("/output")
    configs = [r.config for r in sample_results]
    path = write_raw_configs(configs, Path("/output"))
    assert path.exists()
    assert path.read_text() == "vmess://config1"


def test_write_base64_configs(fs, sample_results: list[ConfigResult]):
    fs.create_dir("/output")
    configs = [r.config for r in sample_results]
    path = write_base64_configs(configs, Path("/output"))
    assert path.exists()
    assert "dm1lc3M6Ly9jb25maWcx" in path.read_text()


@patch("configstream.output_writer.ProxyParser")
def test_write_clash_proxies(MockProxyParser, fs, sample_results: list[ConfigResult]):
    """Test writing Clash proxies with a mocked parser."""
    mock_parser_instance = MockProxyParser.return_value
    mock_parser_instance.config_to_clash_proxy.return_value = {"name": "test"}

    fs.create_dir("/output")
    path = write_clash_proxies(sample_results, Path("/output"))
    assert path.exists()
    assert "proxies:" in path.read_text()
    assert "name: test" in path.read_text()

    MockProxyParser.assert_called_once()
    mock_parser_instance.config_to_clash_proxy.assert_called_once_with(
        sample_results[0].config, 0, sample_results[0].protocol
    )


def test_write_csv_report_content(fs, sample_results: list[ConfigResult]):
    """Test the content of the generated CSV report."""
    fs.create_dir("/output")
    path = write_csv_report(sample_results, Path("/output"))
    assert path.exists()
    content = path.read_text()
    lines = content.strip().split('\n')
    assert len(lines) == 2  # Header + 1 result
    assert lines[0] == 'config,protocol,host,port,ping_ms,reachable,country'
    assert 'vmess://config1,VMess,example.com,443,123.0,True,US' in lines[1]


def test_write_csv_report_content(fs, sample_results: list[ConfigResult]):
    """Test the content of the generated CSV report."""
    fs.create_dir("/output")
    path = write_csv_report(sample_results, Path("/output"))
    assert path.exists()
    content = path.read_text()
    lines = content.strip().split('\n')
    assert len(lines) == 2  # Header + 1 result
    assert lines[0] == 'config,protocol,host,port,ping_ms,reachable,country'
    assert 'vmess://config1,VMess,example.com,443,123.0,True,US' in lines[1]
