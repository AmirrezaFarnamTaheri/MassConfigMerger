from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.core.config_processor import ConfigResult
from massconfigmerger.vpn_retester import (
    filter_configs_by_protocol,
    filter_results_by_ping,
    load_configs_from_file,
    process_results,
    run_retester,
    save_retest_results,
)


def test_load_configs_from_file_raw(tmp_path: Path):
    """Test loading raw config files."""
    p = tmp_path / "raw.txt"
    p.write_text("vmess://config1\nss://config2")
    configs = load_configs_from_file(p)
    assert configs == ["vmess://config1", "ss://config2"]


def test_load_configs_from_file_base64(tmp_path: Path):
    """Test loading base64-encoded config files."""
    p = tmp_path / "b64.txt"
    content = "vmess://config1\nss://config2"
    encoded = base64.b64encode(content.encode()).decode()
    p.write_text(encoded)
    configs = load_configs_from_file(p)
    assert configs == ["vmess://config1", "ss://config2"]


def test_load_configs_from_file_invalid_base64(tmp_path: Path):
    """Test that loading invalid base64 raises a ValueError."""
    p = tmp_path / "invalid.txt"
    p.write_text("this is not base64")
    with pytest.raises(ValueError, match="Failed to decode base64 input"):
        load_configs_from_file(p)


def test_filter_configs_by_protocol():
    """Test the config filtering logic based on protocol."""
    configs = ["vmess://c1", "ss://c2", "trojan://c3"]
    settings = Settings()

    # Test include
    settings.filtering.merge_include_protocols = {"VMESS", "SHADOWSOCKS"}
    settings.filtering.merge_exclude_protocols = set()
    filtered = filter_configs_by_protocol(configs, settings)
    assert filtered == ["vmess://c1", "ss://c2"]

    # Test exclude
    settings.filtering.merge_include_protocols = set()
    settings.filtering.merge_exclude_protocols = {"SHADOWSOCKS"}
    filtered = filter_configs_by_protocol(configs, settings)
    assert filtered == ["vmess://c1", "trojan://c3"]

    # Test no filter
    settings.filtering.merge_include_protocols = set()
    settings.filtering.merge_exclude_protocols = set()
    filtered = filter_configs_by_protocol(configs, settings)
    assert filtered == configs


def test_filter_results_by_ping():
    """Test filtering results by max_ping_ms."""
    results = [
        ConfigResult(config="c1", protocol="VLESS", ping_time=0.1),  # 100ms
        ConfigResult(config="c2", protocol="VLESS", ping_time=0.3),  # 300ms
        ConfigResult(config="c3", protocol="VLESS", ping_time=None),  # Unreachable
    ]
    settings = Settings()
    settings.filtering.max_ping_ms = 200
    filtered = filter_results_by_ping(results, settings)
    assert len(filtered) == 1
    assert filtered[0].config == "c1"

    # Test with no limit
    settings.filtering.max_ping_ms = None
    filtered = filter_results_by_ping(results, settings)
    assert len(filtered) == 3


def test_process_results():
    """Test sorting and top-N filtering of results."""
    results = [
        ConfigResult(config="c1", protocol="VLESS", ping_time=0.3),
        ConfigResult(config="c2", protocol="VLESS", ping_time=0.1),
        ConfigResult(config="c3", protocol="VLESS", ping_time=0.2),
    ]
    settings = Settings()

    # Test sorting
    settings.processing.enable_sorting = True
    settings.processing.top_n = 0
    processed = process_results(results.copy(), settings)
    assert [r.config for r in processed] == ["c2", "c3", "c1"]

    # Test top-N with sorting
    settings.processing.top_n = 2
    processed = process_results(results.copy(), settings)
    assert [r.config for r in processed] == ["c2", "c3"]

    # Test disabled sorting
    settings.processing.enable_sorting = False
    settings.processing.top_n = 0  # Reset top_n
    processed = process_results(results.copy(), settings)
    assert [r.config for r in processed] == ["c1", "c2", "c3"]


@patch("massconfigmerger.vpn_retester.Path.write_text")
@patch("builtins.open", new_callable=mock_open)
def test_save_retest_results(
    mock_open_fn: MagicMock, mock_write_text: MagicMock, tmp_path: Path
):
    """Test the save_retest_results function."""
    results = [
        ConfigResult(
            config="vmess://c1", protocol="VMESS", is_reachable=True, ping_time=0.1
        ),
        ConfigResult(
            config="ss://c2", protocol="SHADOWSOCKS", is_reachable=True, ping_time=0.3
        ),
    ]
    settings = Settings()
    settings.output.output_dir = str(tmp_path)
    settings.output.write_base64 = True
    settings.output.write_csv = True

    save_retest_results(results, settings)

    # raw file should be called with the results
    mock_write_text.assert_any_call("vmess://c1\nss://c2", encoding="utf-8")

    # base64 file should be called with encoded results
    expected_b64 = base64.b64encode(b"vmess://c1\nss://c2").decode()
    mock_write_text.assert_any_call(expected_b64, encoding="utf-8")

    # Check that the CSV file was opened for writing
    mock_open_fn.assert_called_once_with(
        tmp_path / "vpn_retested_detailed.csv", "w", newline="", encoding="utf-8"
    )


@pytest.mark.asyncio
@patch("massconfigmerger.vpn_retester.load_configs_from_file")
@patch("massconfigmerger.vpn_retester.filter_configs_by_protocol")
@patch("massconfigmerger.vpn_retester.retest_configs")
@patch("massconfigmerger.vpn_retester.filter_results_by_ping")
@patch("massconfigmerger.vpn_retester.process_results")
@patch("massconfigmerger.vpn_retester.save_retest_results")
async def test_run_retester_flow(
    mock_save: MagicMock,
    mock_process: MagicMock,
    mock_filter_ping: MagicMock,
    mock_retest: AsyncMock,
    mock_filter_proto: MagicMock,
    mock_load: MagicMock,
):
    """Test the main flow of the run_retester function."""
    # Arrange
    settings = Settings()
    mock_load.return_value = ["c1", "c2", "c3"]
    mock_filter_proto.return_value = ["c1", "c2"]
    mock_retest.return_value = [ConfigResult(config="c1", protocol="VLESS"), ConfigResult(config="c2", protocol="VLESS")]
    mock_filter_ping.return_value = [ConfigResult(config="c1", protocol="VLESS")]
    mock_process.return_value = [
        ConfigResult(config="c1_processed", protocol="VLESS")
    ]

    # Act
    await run_retester(settings, Path("dummy.txt"))

    # Assert
    mock_load.assert_called_once()
    mock_filter_proto.assert_called_once()
    mock_retest.assert_awaited_once()
    mock_filter_ping.assert_called_once()
    mock_process.assert_called_once()
    mock_save.assert_called_once()
    final_results = mock_save.call_args[0][0]
    assert len(final_results) == 1
    assert final_results[0].config == "c1_processed"


@pytest.mark.asyncio
@patch("massconfigmerger.vpn_retester.config_normalizer.extract_host_port")
@patch("massconfigmerger.vpn_retester.ConfigProcessor")
async def test_retest_configs(
    MockConfigProcessor, mock_extract_host_port, tmp_path: Path
):
    """Test the retest_configs function."""
    # Arrange
    from massconfigmerger.vpn_retester import retest_configs

    settings = Settings()
    mock_proc = MockConfigProcessor.return_value
    mock_extract_host_port.side_effect = [("host1", 1234), (None, None)]
    mock_proc.test_connection = AsyncMock(return_value=0.123)
    mock_proc.lookup_country = AsyncMock(return_value="US")
    mock_proc.tester.close = AsyncMock()

    configs = ["config1_valid", "config2_invalid"]

    # Act
    results = await retest_configs(configs, settings)

    # Assert
    assert len(results) == 2
    assert results[0].config == "config1_valid"
    assert results[0].ping_time == 0.123
    assert results[0].is_reachable is True
    assert results[1].config == "config2_invalid"
    assert results[1].ping_time is None
    assert results[1].is_reachable is False
    mock_proc.test_connection.assert_awaited_once_with("host1", 1234)
    mock_proc.tester.close.assert_awaited_once()