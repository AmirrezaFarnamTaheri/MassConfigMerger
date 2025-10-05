from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.vpn_retester import (
    filter_configs,
    load_configs,
    save_results,
    run_retester,
)


def test_load_configs_raw(tmp_path: Path):
    """Test loading raw config files."""
    p = tmp_path / "raw.txt"
    p.write_text("vmess://config1\nss://config2")
    configs = load_configs(p)
    assert configs == ["vmess://config1", "ss://config2"]


def test_load_configs_base64(tmp_path: Path):
    """Test loading base64-encoded config files."""
    p = tmp_path / "b64.txt"
    content = "vmess://config1\nss://config2"
    encoded = base64.b64encode(content.encode()).decode()
    p.write_text(encoded)
    configs = load_configs(p)
    assert configs == ["vmess://config1", "ss://config2"]


def test_load_configs_invalid_base64(tmp_path: Path):
    """Test that loading invalid base64 raises a ValueError."""
    p = tmp_path / "invalid.txt"
    p.write_text("this is not base64")
    with pytest.raises(ValueError, match="Failed to decode base64 input"):
        load_configs(p)


def test_filter_configs():
    """Test the config filtering logic."""
    configs = ["vmess://c1", "ss://c2", "trojan://c3"]
    settings = Settings()

    # Test include
    settings.filtering.merge_include_protocols = {"VMESS", "SHADOWSOCKS"}
    settings.filtering.merge_exclude_protocols = set()
    filtered = filter_configs(configs, settings)
    assert filtered == ["vmess://c1", "ss://c2"]

    # Test exclude
    settings.filtering.merge_include_protocols = set()
    settings.filtering.merge_exclude_protocols = {"SHADOWSOCKS"}
    filtered = filter_configs(configs, settings)
    assert filtered == ["vmess://c1", "trojan://c3"]

    # Test no filter
    settings.filtering.merge_include_protocols = None
    settings.filtering.merge_exclude_protocols = None
    filtered = filter_configs(configs, settings)
    assert filtered == configs


@patch("massconfigmerger.vpn_retester.Path.write_text")
@patch("builtins.open", new_callable=mock_open)
def test_save_results(mock_open: MagicMock, mock_write_text: MagicMock, tmp_path: Path):
    """Test the save_results function."""
    results = [("vmess://c1", 0.1), ("ss://c2", 0.3), ("trojan://c3", 0.2)]
    settings = Settings()
    settings.output.output_dir = str(tmp_path)
    settings.output.write_base64 = True
    settings.output.write_csv = True
    settings.processing.enable_sorting = True
    settings.processing.top_n = 2

    # Test with sorting and top_n
    save_results(results, settings)

    # raw file should be called with sorted, trimmed results
    mock_write_text.assert_any_call("vmess://c1\ntrojan://c3", encoding="utf-8")

    # base64 file should be called with sorted, trimmed, encoded results
    expected_b64 = base64.b64encode(b"vmess://c1\ntrojan://c3").decode()
    mock_write_text.assert_any_call(expected_b64, encoding="utf-8")

    # Check that the CSV file was opened for writing
    mock_open.assert_called_once_with(tmp_path / "vpn_retested_detailed.csv", "w", newline="", encoding="utf-8")


@pytest.mark.asyncio
@patch("massconfigmerger.vpn_retester.load_configs")
@patch("massconfigmerger.vpn_retester.filter_configs")
@patch("massconfigmerger.vpn_retester.retest_configs")
@patch("massconfigmerger.vpn_retester.save_results")
async def test_run_retester_flow(
    mock_save: MagicMock,
    mock_retest: MagicMock,
    mock_filter: MagicMock,
    mock_load: MagicMock,
):
    """Test the main flow of the run_retester function."""
    # Arrange
    settings = Settings()
    settings.filtering.max_ping_ms = 200

    mock_load.return_value = ["vmess://c1", "ss://c2", "trojan://c3"]
    mock_filter.return_value = ["vmess://c1", "ss://c2"]
    mock_retest.return_value = [
        ("vmess://c1", 0.1),  # Will be kept
        ("ss://c2", 0.3),     # Will be filtered by max_ping
    ]

    # Act
    await run_retester(settings, Path("dummy.txt"))

    # Assert
    mock_load.assert_called_once()
    mock_filter.assert_called_once()
    mock_retest.assert_awaited_once()

    # save_results should be called with the final, ping-filtered results
    mock_save.assert_called_once()
    final_results = mock_save.call_args[0][0]
    assert final_results == [("vmess://c1", 0.1)]


@pytest.mark.asyncio
@patch("massconfigmerger.vpn_retester.ConfigProcessor")
async def test_retest_configs(MockConfigProcessor, tmp_path: Path):
    """Test the retest_configs function."""
    # Arrange
    from massconfigmerger.vpn_retester import retest_configs

    settings = Settings()
    mock_proc = MockConfigProcessor.return_value
    # Simulate one config with host/port, one without
    mock_proc.extract_host_port.side_effect = [("host1", 1234), (None, None)]
    # Simulate a successful ping for the first config
    mock_proc.test_connection = AsyncMock(return_value=0.123)
    mock_proc.tester.close = AsyncMock()

    configs = ["config1_valid", "config2_invalid"]

    # Act
    results = await retest_configs(configs, settings)

    # Assert
    assert len(results) == 2
    assert results[0] == ("config1_valid", 0.123)
    assert results[1] == ("config2_invalid", None)
    mock_proc.test_connection.assert_awaited_once_with("host1", 1234)
    mock_proc.tester.close.assert_awaited_once()