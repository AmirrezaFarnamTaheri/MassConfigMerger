from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from massconfigmerger.cli import main, build_parser, _update_settings_from_args
from massconfigmerger.config import Settings


@patch("massconfigmerger.commands.pipeline.run_aggregation_pipeline", new_callable=AsyncMock)
@patch("massconfigmerger.commands.vpn_merger.run_merger", new_callable=AsyncMock)
def test_cli_full_command(mock_run_merger, mock_run_agg_pipeline, fs):
    """Test the 'full' command and its argument parsing."""
    mock_run_agg_pipeline.return_value = (Path("fake_output"), [])
    fs.create_file("config.yaml")
    fs.create_file("sources.txt")
    fs.create_file("channels.txt")
    fs.create_file("fake_output/vpn_subscription_raw.txt")

    cli_args = [
        "full",
        "--concurrent-limit", "50",
        "--request-timeout", "25",
        "--no-sort",
        "--top-n", "100",
        "--include-pattern", "US",
        "--exclude-pattern", "RU",
        "--fetch-protocols", "vmess,ss",
        "--include-protocols", "VLESS,TROJAN",
        "--exclude-protocols", "SHADOWSOCKS",
    ]

    main(cli_args)

    mock_run_agg_pipeline.assert_awaited_once()
    mock_run_merger.assert_awaited_once()

    agg_args, _ = mock_run_agg_pipeline.call_args
    called_settings: Settings = agg_args[0]

    assert called_settings.network.concurrent_limit == 50
    assert called_settings.network.request_timeout == 25
    assert called_settings.processing.enable_sorting is False
    assert called_settings.processing.top_n == 100
    assert "US" in called_settings.filtering.include_patterns
    assert "RU" in called_settings.filtering.exclude_patterns
    assert set(called_settings.filtering.fetch_protocols) == {"VMESS", "SS"}
    assert called_settings.filtering.merge_include_protocols == {"VLESS", "TROJAN"}
    assert called_settings.filtering.merge_exclude_protocols == {"SHADOWSOCKS"}


@patch("massconfigmerger.commands.pipeline.run_aggregation_pipeline", new_callable=AsyncMock)
def test_cli_fetch_command(mock_run_agg_pipeline, fs):
    """Test the 'fetch' command."""
    fs.create_file("config.yaml")
    fs.create_file("sources.txt")
    main(["fetch"])
    mock_run_agg_pipeline.assert_awaited_once()


@patch("massconfigmerger.commands.vpn_merger.run_merger", new_callable=AsyncMock)
def test_cli_merge_command(mock_run_merger, fs):
    """Test the 'merge' command."""
    fs.create_file("config.yaml")
    fs.create_file("sources.txt")
    main(["merge", "--resume", "my_configs.txt"])
    mock_run_merger.assert_awaited_once()
    _args, kwargs = mock_run_merger.call_args
    assert kwargs["resume_file"] == Path("my_configs.txt")


@patch("massconfigmerger.commands.vpn_retester.run_retester", new_callable=AsyncMock)
def test_cli_retest_command(mock_run_retester, fs):
    """Test the 'retest' command."""
    fs.create_file("config.yaml")
    fs.create_file("my_configs.txt")
    main(["retest", "my_configs.txt"])
    mock_run_retester.assert_awaited_once()
    _, kwargs = mock_run_retester.call_args
    assert kwargs["input_file"] == Path("my_configs.txt")


@patch("massconfigmerger.cli.load_config", side_effect=FileNotFoundError)
def test_cli_config_not_found(mock_load_config, fs):
    """Test that default Settings are used when the config file is not found."""
    fs.create_file("sources.txt")
    fs.create_file("channels.txt")
    mock_handler = MagicMock()

    with patch.dict("massconfigmerger.cli.HANDLERS", {"full": mock_handler}):
        main(["full"])

    mock_handler.assert_called_once()
    args, _ = mock_handler.call_args
    cfg_instance = args[1]
    assert isinstance(cfg_instance, Settings)
    assert cfg_instance.network.concurrent_limit == 20


def test_cli_sources_list_command(fs):
    """Test the 'sources list' command."""
    fs.create_file("sources.txt")
    mock_handler = MagicMock()
    with patch.dict("massconfigmerger.cli.SOURCES_HANDLERS", {"list": mock_handler}):
        main(["sources", "--sources-file", "sources.txt", "list"])
    mock_handler.assert_called_once()


def test_cli_sources_add_command(fs):
    """Test the 'sources add' command."""
    fs.create_file("sources.txt")
    mock_handler = MagicMock()
    with patch.dict("massconfigmerger.cli.SOURCES_HANDLERS", {"add": mock_handler}):
        main(["sources", "--sources-file", "sources.txt", "add", "http://example.com/source"])
    mock_handler.assert_called_once()
    args = mock_handler.call_args[0][0]
    assert args.url == "http://example.com/source"


def test_cli_sources_remove_command(fs):
    """Test the 'sources remove' command."""
    fs.create_file("sources.txt", contents="http://example.com/source\n")
    mock_handler = MagicMock()
    with patch.dict("massconfigmerger.cli.SOURCES_HANDLERS", {"remove": mock_handler}):
        main(["sources", "--sources-file", "sources.txt", "remove", "http://example.com/source"])
    mock_handler.assert_called_once()
    args = mock_handler.call_args[0][0]
    assert args.url == "http://example.com/source"