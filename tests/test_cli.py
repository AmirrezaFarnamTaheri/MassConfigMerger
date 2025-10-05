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


@patch("massconfigmerger.cli.load_config", side_effect=FileNotFoundError)
@patch("massconfigmerger.cli.Settings")
def test_cli_config_not_found(MockSettings, mock_load_config, fs):
    """Test the CLI's behavior when the config file is not found."""
    # Arrange
    # Configure the mock Settings object to have a config_file attribute that is None
    mock_settings_instance = MockSettings.return_value
    mock_settings_instance.config_file = None

    fs.create_file("sources.txt")
    fs.create_file("channels.txt")

    # Act
    with patch("massconfigmerger.cli._handle_full") as mock_handler:
        main(["full"])

        # Assert
        mock_handler.assert_called_once()
        args, _ = mock_handler.call_args
        settings_instance: Settings = args[1]
        assert settings_instance.config_file is None