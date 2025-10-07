from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from configstream.cli import main, build_parser, _update_settings_from_args
from configstream.config import Settings


@patch("configstream.commands.services.run_full_pipeline", new_callable=AsyncMock)
def test_cli_full_command(mock_run_full_pipeline, fs):
    """Test the 'full' command and its argument parsing."""
    fs.create_file("config.yaml")
    fs.create_file("sources.txt")
    fs.create_file("channels.txt")

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

    mock_run_full_pipeline.assert_awaited_once()

    _args, kwargs = mock_run_full_pipeline.call_args
    called_settings: Settings = _args[0]

    assert called_settings.network.concurrent_limit == 50
    assert called_settings.network.request_timeout == 25
    assert called_settings.processing.enable_sorting is False
    assert called_settings.processing.top_n == 100
    assert "US" in called_settings.filtering.include_patterns
    assert "RU" in called_settings.filtering.exclude_patterns
    assert set(called_settings.filtering.fetch_protocols) == {"VMESS", "SS"}
    assert called_settings.filtering.merge_include_protocols == {"VLESS", "TROJAN"}
    assert called_settings.filtering.merge_exclude_protocols == {"SHADOWSOCKS"}


@patch("configstream.commands.services.run_fetch_pipeline", new_callable=AsyncMock)
def test_cli_fetch_command(mock_run_fetch_pipeline, fs):
    """Test the 'fetch' command."""
    fs.create_file("config.yaml")
    fs.create_file("sources.txt")
    main(["fetch"])
    mock_run_fetch_pipeline.assert_awaited_once()


@patch("configstream.commands.services.run_merge_pipeline", new_callable=AsyncMock)
def test_cli_merge_command(mock_run_merge_pipeline, fs):
    """Test the 'merge' command."""
    fs.create_file("config.yaml")
    fs.create_file("sources.txt")
    main(["merge", "--resume", "my_configs.txt"])
    mock_run_merge_pipeline.assert_awaited_once()
    _args, kwargs = mock_run_merge_pipeline.call_args
    assert kwargs["resume_file"] == Path("my_configs.txt")


@patch("configstream.commands.services.run_retest_pipeline", new_callable=AsyncMock)
def test_cli_retest_command(mock_run_retest_pipeline, fs):
    """Test the 'retest' command."""
    fs.create_file("config.yaml")
    fs.create_file("my_configs.txt")
    main(["retest", "my_configs.txt"])
    mock_run_retest_pipeline.assert_awaited_once()
    _args, kwargs = mock_run_retest_pipeline.call_args
    assert kwargs["input_file"] == Path("my_configs.txt")


@patch("configstream.cli.load_config", side_effect=FileNotFoundError)
def test_cli_config_not_found(mock_load_config, fs):
    """Test that default Settings are used when the config file is not found."""
    fs.create_file("sources.txt")
    fs.create_file("channels.txt")
    mock_handler = MagicMock()

    with patch.dict("configstream.cli.HANDLERS", {"full": mock_handler}):
        main(["full"])

    mock_handler.assert_called_once()
    args, _ = mock_handler.call_args
    cfg_instance = args[1]
    assert isinstance(cfg_instance, Settings)
    assert cfg_instance.network.concurrent_limit == 20


@patch("configstream.services.list_sources")
def test_cli_sources_list_command(mock_list_sources, fs):
    """Test the 'sources list' command."""
    fs.create_file("sources.txt")
    with patch("configstream.cli.services.list_sources", mock_list_sources):
        main(["sources", "--sources-file", "sources.txt", "list"])
    mock_list_sources.assert_called_once_with(Path("sources.txt"))


@patch("configstream.services.add_new_source")
def test_cli_sources_add_command(mock_add_source, fs):
    """Test the 'sources add' command."""
    fs.create_file("sources.txt")
    with patch("configstream.cli.services.add_new_source", mock_add_source):
        main(["sources", "--sources-file", "sources.txt", "add", "http://example.com/source"])
    mock_add_source.assert_called_once_with(Path("sources.txt"), "http://example.com/source")


from configstream.cli import _parse_protocol_list, _parse_protocol_set


@patch("configstream.services.remove_existing_source")
def test_cli_sources_remove_command(mock_remove_source, fs):
    """Test the 'sources remove' command."""
    fs.create_file("sources.txt", contents="http://example.com/source\n")
    with patch("configstream.cli.services.remove_existing_source", mock_remove_source):
        main(["sources", "--sources-file", "sources.txt", "remove", "http://example.com/source"])
    mock_remove_source.assert_called_once_with(Path("sources.txt"), "http://example.com/source")


def test_parse_protocol_list_with_list_input():
    """Test _parse_protocol_list with a list input."""
    protocols = ["VLESS", " trojan ", " ss"]
    parsed = _parse_protocol_list(protocols)
    assert parsed == ["VLESS", "TROJAN", "SS"]


def test_parse_protocol_set_with_list_input():
    """Test _parse_protocol_set with a list input."""
    protocols = ["VLESS", " trojan ", " ss", "VLESS"]
    parsed = _parse_protocol_set(protocols)
    assert parsed == {"VLESS", "TROJAN", "SS"}


@patch("configstream.cli.load_config", side_effect=ValueError("Invalid config"))
def test_cli_config_value_error(mock_load_config, capsys, fs):
    """Test that default Settings are used when the config file is invalid."""
    fs.create_file("sources.txt")
    fs.create_file("channels.txt")
    mock_handler = MagicMock()

    with patch.dict("configstream.cli.HANDLERS", {"full": mock_handler}):
        main(["full"])

    mock_handler.assert_called_once()
    captured = capsys.readouterr()
    assert "Config file not found" in captured.out


@patch("configstream.commands.handle_fetch")
@patch("configstream.cli.load_config")
def test_main_entrypoint(mock_load_config, mock_handle_fetch, fs):
    """Test that the main entry point calls main()."""
    import argparse
    import runpy

    fs.create_file("config.yaml")
    mock_load_config.return_value = Settings()

    with patch("sys.argv", ["configstream", "fetch"]):
        runpy.run_module("configstream.cli", run_name="__main__")

    mock_handle_fetch.assert_called_once()
    args, kwargs = mock_handle_fetch.call_args
    assert isinstance(args[0], argparse.Namespace)
    assert isinstance(args[1], Settings)


@patch("configstream.services.remove_existing_source")
@patch("configstream.services.add_new_source")
@patch("configstream.services.list_sources")
def test_cli_sources_unknown_command(mock_list, mock_add, mock_remove, fs):
    """Test the 'sources' command with an unknown subcommand."""
    fs.create_file("sources.txt")
    with patch("configstream.cli.services.list_sources", mock_list), \
         patch("configstream.cli.services.add_new_source", mock_add), \
         patch("configstream.cli.services.remove_existing_source", mock_remove):
        with pytest.raises(SystemExit):
            main(["sources", "--sources-file", "sources.txt", "unknown"])
    mock_list.assert_not_called()
    mock_add.assert_not_called()
    mock_remove.assert_not_called()


def test_parse_protocol_list_empty_input():
    """Test _parse_protocol_list with empty and None inputs."""
    assert _parse_protocol_list(None) == []
    assert _parse_protocol_list("") == []


def test_parse_protocol_set_empty_input():
    """Test _parse_protocol_set with empty and None inputs."""
    assert _parse_protocol_set(None) == set()
    assert _parse_protocol_set("") == set()