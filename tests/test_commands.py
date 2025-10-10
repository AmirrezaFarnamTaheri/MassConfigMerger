import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import argparse
from pathlib import Path

from configstream.commands import (
    handle_fetch,
    handle_merge,
    handle_retest,
    handle_full,
    handle_tui,
)
from configstream.config import Settings


@pytest.fixture
def mock_args():
    """Fixture for a mock argparse.Namespace object."""
    args = argparse.Namespace()
    args.sources = "sources.txt"
    args.channels = "channels.txt"
    args.hours = 24
    args.failure_threshold = 3
    args.no_prune = False
    args.resume_file = "resume.json"
    args.input = "input.txt"
    args.interval = 2
    args.port = 8080
    args.host = "0.0.0.0"
    args.data_dir = "./data"
    return args


@pytest.fixture
def mock_settings():
    """Fixture for a mock Settings object."""
    settings = MagicMock(spec=Settings)
    settings.output = MagicMock()
    settings.output.output_dir = "/fake/output"
    return settings


@patch("configstream.commands.services", new_callable=MagicMock)
def test_handle_fetch(mock_services, mock_args, mock_settings):
    """Test the fetch command handler."""
    mock_services.run_fetch_pipeline = AsyncMock()
    handle_fetch(mock_args, mock_settings)
    mock_services.run_fetch_pipeline.assert_awaited_once_with(
        mock_settings,
        sources_file=Path(mock_args.sources),
        channels_file=Path(mock_args.channels),
        last_hours=mock_args.hours,
        failure_threshold=mock_args.failure_threshold,
        prune=True,
    )


@patch("configstream.commands.services", new_callable=MagicMock)
def test_handle_merge(mock_services, mock_args, mock_settings):
    """Test the merge command handler."""
    mock_services.run_merge_pipeline = AsyncMock()
    handle_merge(mock_args, mock_settings)
    mock_services.run_merge_pipeline.assert_awaited_once_with(
        mock_settings,
        sources_file=Path(mock_args.sources),
        resume_file=Path(mock_args.resume_file),
    )


@patch("configstream.commands.services", new_callable=MagicMock)
def test_handle_retest(mock_services, mock_args, mock_settings):
    """Test the retest command handler."""
    mock_services.run_retest_pipeline = AsyncMock()
    handle_retest(mock_args, mock_settings)
    mock_services.run_retest_pipeline.assert_awaited_once_with(
        mock_settings, input_file=Path(mock_args.input)
    )


@patch("configstream.commands.services", new_callable=MagicMock)
def test_handle_full(mock_services, mock_args, mock_settings):
    """Test the full command handler."""
    mock_services.run_full_pipeline = AsyncMock()
    handle_full(mock_args, mock_settings)
    mock_services.run_full_pipeline.assert_awaited_once_with(
        mock_settings,
        sources_file=Path(mock_args.sources),
        channels_file=Path(mock_args.channels),
        last_hours=mock_args.hours,
        failure_threshold=mock_args.failure_threshold,
        prune=True,
    )


@patch("configstream.commands.display_results")
def test_handle_tui(mock_display_results, mock_args, mock_settings, fs):
    """Test the tui command handler."""
    expected_path = Path(mock_settings.output.output_dir) / "current_results.json"
    fs.create_file(expected_path)

    handle_tui(mock_args, mock_settings)

    mock_display_results.assert_called_once_with(expected_path)