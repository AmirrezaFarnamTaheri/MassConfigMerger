"""Test coverage for command handlers in commands.py."""
import argparse
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

from configstream.commands import handle_fetch, handle_merge, handle_retest, handle_full, handle_tui, cmd_daemon
from configstream.config import Settings


@pytest.fixture
def mock_args():
    """Returns a mock argparse.Namespace object with default values."""
    return argparse.Namespace(
        sources="sources.txt",
        channels="channels.txt",
        hours=24,
        failure_threshold=3,
        no_prune=False,
        resume_file=None,
        input="input.txt",
        data_dir="/tmp/data",
        interval=1,
        host="localhost",
        port=8080,
    )


@pytest.fixture
def mock_settings():
    """Returns a mock Settings object."""
    return Settings()


@patch("configstream.services.run_fetch_pipeline", new_callable=AsyncMock)
def test_handle_fetch(mock_run_fetch, mock_args, mock_settings):
    """Test the handle_fetch command handler."""
    handle_fetch(mock_args, mock_settings)
    mock_run_fetch.assert_called_once_with(
        mock_settings,
        sources_file=Path(mock_args.sources),
        channels_file=Path(mock_args.channels),
        last_hours=mock_args.hours,
        failure_threshold=mock_args.failure_threshold,
        prune=not mock_args.no_prune,
    )


@patch("configstream.services.run_merge_pipeline", new_callable=AsyncMock)
def test_handle_merge(mock_run_merge, mock_args, mock_settings):
    """Test the handle_merge command handler."""
    handle_merge(mock_args, mock_settings)
    mock_run_merge.assert_called_once_with(
        mock_settings,
        sources_file=Path(mock_args.sources),
        resume_file=None,
    )


@patch("configstream.services.run_merge_pipeline", new_callable=AsyncMock)
def test_handle_merge_with_resume(mock_run_merge, mock_args, mock_settings):
    """Test the handle_merge command handler with a resume file."""
    mock_args.resume_file = "resume.txt"
    handle_merge(mock_args, mock_settings)
    mock_run_merge.assert_called_once_with(
        mock_settings,
        sources_file=Path(mock_args.sources),
        resume_file=Path("resume.txt"),
    )


@patch("configstream.services.run_retest_pipeline", new_callable=AsyncMock)
def test_handle_retest(mock_run_retest, mock_args, mock_settings):
    """Test the handle_retest command handler."""
    handle_retest(mock_args, mock_settings)
    mock_run_retest.assert_called_once_with(
        mock_settings, input_file=Path("input.txt")
    )


@patch("configstream.services.run_full_pipeline", new_callable=AsyncMock)
def test_handle_full(mock_run_full, mock_args, mock_settings):
    """Test the handle_full command handler."""
    handle_full(mock_args, mock_settings)
    mock_run_full.assert_called_once()


@patch("configstream.commands.display_results")
def test_handle_tui(mock_display_results, fs, mock_settings):
    """Test the handle_tui command handler."""
    output_dir = Path(mock_settings.output.output_dir)
    fs.create_dir(output_dir)
    results_file = output_dir / "current_results.json"
    fs.create_file(results_file)

    handle_tui(argparse.Namespace(), mock_settings)
    mock_display_results.assert_called_once_with(results_file)


@patch("configstream.commands.TestScheduler")
@patch("configstream.commands.app.run", side_effect=Exception("Test server error"))
@patch("configstream.commands.sys.exit")
def test_cmd_daemon_server_exception(mock_exit, mock_app_run, MockScheduler, mock_args, mock_settings):
    """Test that cmd_daemon handles exceptions from app.run gracefully."""
    scheduler_instance = MockScheduler.return_value

    cmd_daemon(mock_args, mock_settings)

    scheduler_instance.start.assert_called_once_with(interval_hours=mock_args.interval)
    mock_app_run.assert_called_once()
    scheduler_instance.stop.assert_called_once()
    mock_exit.assert_called_once_with(1)