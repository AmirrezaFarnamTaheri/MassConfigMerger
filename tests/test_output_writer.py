from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.core.config_processor import ConfigResult
from massconfigmerger.output_writer import (
    write_all_outputs,
    write_base64_configs,
    write_clash_proxies,
    write_csv_report,
    write_raw_configs,
)
from massconfigmerger.report_generator import generate_html_report


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
            source_url="http://source.com",
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

@patch("massconfigmerger.output_writer.config_to_clash_proxy", return_value={"name": "test"})
def test_write_clash_proxies(mock_to_clash, fs, sample_results: list[ConfigResult]):
    fs.create_dir("/output")
    path = write_clash_proxies(sample_results, Path("/output"))
    assert path.exists()
    assert "proxies:" in path.read_text()
    mock_to_clash.assert_called()


@patch("massconfigmerger.output_writer.generate_json_report")
@patch("massconfigmerger.output_writer.generate_html_report")
@patch("massconfigmerger.output_writer.write_clash_proxies")
@patch("massconfigmerger.output_writer.write_csv_report")
@patch("massconfigmerger.output_writer.write_base64_configs")
@patch("massconfigmerger.output_writer.write_raw_configs")
def test_write_all_outputs(
    mock_raw, mock_b64, mock_csv, mock_clash, mock_html, mock_json, fs
):
    """Test the main orchestrator function for writing all outputs."""
    fs.create_dir("/output")
    settings = Settings()
    # Enable all options to test all branches
    settings.output.write_base64 = True
    settings.output.write_csv = True
    settings.output.write_html = True
    settings.output.write_clash_proxies = True
    settings.output.surge_file = "surge.conf"
    settings.output.qx_file = "qx.conf"

    results = [ConfigResult(config="c1", protocol="p1")]
    stats = {"s": 1}
    start_time = 0

    written_files = write_all_outputs(results, settings, stats, start_time)

    # Check that all the main writer functions were called
    mock_raw.assert_called_once()
    mock_b64.assert_called_once()
    mock_csv.assert_called_once()
    mock_clash.assert_called_once()
    mock_html.assert_called_once()
    mock_json.assert_called_once()

    # 2 base files + 4 optional files
    assert len(written_files) == 6


def test_write_csv_report_content(fs, sample_results: list[ConfigResult]):
    """Test the content of the generated CSV report."""
    fs.create_dir("/output")
    path = write_csv_report(sample_results, Path("/output"))
    assert path.exists()
    content = path.read_text()
    lines = content.strip().split('\n')
    assert len(lines) == 2 # Header + 1 result
    assert lines[0] == 'config,protocol,host,port,ping_ms,reachable,source_url,country'
    assert 'vmess://config1,VMess,example.com,443,123.0,True,http://source.com,US' in lines[1]