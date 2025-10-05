from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

from massconfigmerger.cli import main
from massconfigmerger.config import Settings


@patch("massconfigmerger.cli.pipeline.run_aggregation_pipeline", new_callable=AsyncMock)
@patch("massconfigmerger.cli.vpn_merger.run_merger")
def test_cli_full_command(mock_run_merger, mock_run_agg_pipeline, fs):
    """Test the 'full' command and its argument parsing."""
    # Arrange
    mock_run_agg_pipeline.return_value = (Path("fake_output"), [])
    # The mock for run_merger is synchronous in the test, so we don't need an awaitable here.
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
        "--include-pattern", "UK",
        "--fetch-protocols", "vmess,ss",
    ]

    # Act
    main(cli_args)

    # Assert
    mock_run_agg_pipeline.assert_awaited_once()
    mock_run_merger.assert_called_once()

    # Check that settings were correctly passed to the pipeline
    agg_args, agg_kwargs = mock_run_agg_pipeline.call_args
    called_settings: Settings = agg_args[0]

    assert called_settings.network.concurrent_limit == 50
    assert called_settings.network.request_timeout == 25
    assert called_settings.processing.enable_sorting is False
    assert called_settings.processing.top_n == 100
    assert "US" in called_settings.filtering.include_patterns
    assert "UK" in called_settings.filtering.include_patterns
    assert set(called_settings.filtering.fetch_protocols) == {"VMESS", "SS"}


@patch("massconfigmerger.cli.pipeline.run_aggregation_pipeline", new_callable=AsyncMock)
def test_cli_fetch_command(mock_run_agg_pipeline, fs):
    """Test the 'fetch' command."""
    fs.create_file("config.yaml")
    fs.create_file("sources.txt")

    main(["fetch"])

    mock_run_agg_pipeline.assert_awaited_once()


@patch("massconfigmerger.cli.vpn_merger.run_merger")
def test_cli_merge_command(mock_run_merger, fs):
    """Test the 'merge' command."""
    fs.create_file("config.yaml")
    fs.create_file("sources.txt")
    mock_run_merger.return_value = asyncio.sleep(0) # Make it awaitable for asyncio.run

    main(["merge", "--resume", "my_configs.txt"])

    mock_run_merger.assert_called_once()
    _, kwargs = mock_run_merger.call_args
    assert kwargs["resume_file"] == Path("my_configs.txt")


@patch("massconfigmerger.cli.vpn_retester.run_retester")
def test_cli_retest_command(mock_run_retester, fs):
    """Test the 'retest' command."""
    fs.create_file("config.yaml")
    fs.create_file("my_configs.txt")
    mock_run_retester.return_value = asyncio.sleep(0) # Make it awaitable

    main(["retest", "my_configs.txt"])

    mock_run_retester.assert_called_once()
    # The first argument is the settings object, the second is the input file
    # We are checking the keyword argument here.
    _, kwargs = mock_run_retester.call_args
    assert kwargs["input_file"] == Path("my_configs.txt")


from unittest.mock import patch, AsyncMock, MagicMock


@patch("massconfigmerger.cli.load_config", side_effect=FileNotFoundError)
def test_cli_config_not_found(mock_load_config, fs):
    """Test that default Settings are used when the config file is not found."""
    # Arrange
    fs.create_file("sources.txt")
    fs.create_file("channels.txt")
    mock_handler = MagicMock()

    # Act
    with patch.dict("massconfigmerger.cli.HANDLERS", {"full": mock_handler}):
        main(["full"])

    # Assert
    mock_handler.assert_called_once()
    args, _ = mock_handler.call_args
    cfg_instance = args[1]
    assert isinstance(cfg_instance, Settings)
    # Verify it's a default instance
    assert cfg_instance.network.concurrent_limit == 20


import sys
import runpy
from massconfigmerger.cli import (
    _parse_protocol_list,
    _parse_protocol_set,
    _update_settings_from_args,
    _handle_sources_list,
    _handle_sources_add,
    _handle_sources_remove,
)
import argparse

def test_parse_protocol_list():
    """Test the _parse_protocol_list helper function."""
    assert _parse_protocol_list(None) == []
    assert _parse_protocol_list(["VLESS", "ss"]) == ["VLESS", "SS"]


def test_parse_protocol_set():
    """Test the _parse_protocol_set helper function."""
    assert _parse_protocol_set(None) == set()
    assert _parse_protocol_set(["VLESS", "ss"]) == {"VLESS", "SS"}


def test_update_settings_from_args():
    """Test that _update_settings_from_args correctly updates settings."""
    settings = Settings()
    args = argparse.Namespace(
        concurrent_limit=100,
        request_timeout=30,
        connect_timeout=5.0,
        max_ping_ms=500,
        fetch_protocols="vless,ss",
        merge_include_protocols="vless",
        merge_exclude_protocols="ss",
        output_dir="/tmp/output",
        surge_file="surge.conf",
        qx_file="qx.conf",
        write_base64=False,
        write_csv=False,
        upload_gist=True,
        top_n=50,
        shuffle_sources=True,
        resume_file="resume.txt",
        enable_sorting=False,
        include_patterns=["US"],
        exclude_patterns=["CN"],
    )

    _update_settings_from_args(settings, args)

    assert settings.network.concurrent_limit == 100
    assert settings.filtering.fetch_protocols == ["VLESS", "SS"]
    assert settings.filtering.merge_include_protocols == {"VLESS"}
    assert settings.filtering.merge_exclude_protocols == {"SS"}
    assert "US" in settings.filtering.include_patterns
    assert "CN" in settings.filtering.exclude_patterns


def test_handle_sources_list_empty(fs, capsys):
    """Test the 'sources list' command with an empty sources file."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file))
    _handle_sources_list(args)
    captured = capsys.readouterr()
    assert "No sources found" in captured.out


def test_handle_sources_add_invalid_url(fs, capsys):
    """Test the 'sources add' command with an invalid URL."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file), url="invalid-url")
    _handle_sources_add(args)
    captured = capsys.readouterr()
    assert "Invalid URL" in captured.out


def test_handle_sources_add_duplicate(fs, capsys):
    """Test the 'sources add' command with a duplicate URL."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://example.com/sub")
    args = argparse.Namespace(sources_file=str(sources_file), url="http://example.com/sub")
    _handle_sources_add(args)
    captured = capsys.readouterr()
    assert "Source already exists" in captured.out


def test_handle_sources_remove_not_found(fs, capsys):
    """Test the 'sources remove' command when the source is not found."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file), url="http://example.com/sub")
    _handle_sources_remove(args)
    captured = capsys.readouterr()
    assert "Source not found" in captured.out


def test_handle_sources_add_success(fs, capsys):
    """Test a successful source addition."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file), url="http://example.com/new")
    _handle_sources_add(args)
    captured = capsys.readouterr()
    assert "Source added" in captured.out
    with open(sources_file) as f:
        assert "http://example.com/new" in f.read()


def test_handle_sources_remove_success(fs, capsys):
    """Test a successful source removal."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://example.com/to-remove\n")
    args = argparse.Namespace(sources_file=str(sources_file), url="http://example.com/to-remove")
    _handle_sources_remove(args)
    captured = capsys.readouterr()
    assert "Source removed" in captured.out
    with open(sources_file) as f:
        assert "http://example.com/to-remove" not in f.read()


def test_handle_sources_remove_invalid_url(fs, capsys):
    """Test removing a source with an invalid URL."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    args = argparse.Namespace(sources_file=str(sources_file), url="not-a-url")
    _handle_sources_remove(args)
    captured = capsys.readouterr()
    assert "Invalid URL format" in captured.out
