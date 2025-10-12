import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import argparse
from pathlib import Path

from configstream.commands import (
    handle_fetch,
    handle_merge,
    handle_retest,
    handle_full,
    handle_daemon,
    handle_tui,
    handle_history,
    handle_prometheus,
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
    args.interval_hours = 2
    args.web_port = 8080
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


@patch("configstream.commands.ConfigStreamDaemon")
@patch("configstream.commands.asyncio")
def test_handle_daemon_no_running_loop(mock_asyncio, mock_daemon_cls, mock_args, mock_settings):
    """Test the daemon command handler when no event loop is running."""
    mock_asyncio.get_running_loop.side_effect = RuntimeError
    mock_daemon_instance = mock_daemon_cls.return_value

    handle_daemon(mock_args, mock_settings)

    mock_daemon_cls.assert_called_once()
    mock_daemon_instance.start.assert_called_once_with(
        interval_hours=mock_args.interval_hours, web_port=mock_args.web_port
    )
    mock_asyncio.run.assert_called_once_with(mock_daemon_instance.start.return_value)


@patch("configstream.commands.ConfigStreamDaemon")
@patch("configstream.commands.asyncio")
def test_handle_daemon_with_running_loop(mock_asyncio, mock_daemon_cls, mock_args, mock_settings):
    """Test the daemon command handler when an event loop is already running."""
    mock_loop = MagicMock()
    mock_asyncio.get_running_loop.return_value = mock_loop
    mock_daemon_instance = mock_daemon_cls.return_value

    handle_daemon(mock_args, mock_settings)

    mock_daemon_cls.assert_called_once()
    mock_daemon_instance.start.assert_called_once_with(
        interval_hours=mock_args.interval_hours, web_port=mock_args.web_port
    )
    mock_loop.create_task.assert_called_once_with(mock_daemon_instance.start.return_value)


@patch("configstream.commands.display_results")
def test_handle_tui(mock_display_results, mock_args, mock_settings, fs):
    """Test the tui command handler."""
    expected_path = Path(mock_settings.output.output_dir) / "current_results.json"
    fs.create_file(expected_path)

    handle_tui(mock_args, mock_settings)

    mock_display_results.assert_called_once_with(expected_path)


@patch("configstream.commands.HistoricalManager", autospec=True)
def test_handle_history_db_exists(mock_manager, mock_args, mock_settings, fs, capsys):
    """Test history command when database exists and nodes are found."""
    db_path = Path(mock_settings.output.output_dir) / "history.db"
    fs.create_file(db_path)
    mock_args.min_score = 80
    mock_args.limit = 5
    mock_args.days_active = 7

    mock_instance = mock_manager.return_value
    mock_node = MagicMock(
        protocol="test", ip="1.1.1.1", port=1234, reliability_score=95.5, uptime_percent=99.1
    )
    mock_instance.get_reliable_nodes.return_value = [mock_node]

    handle_history(mock_args, mock_settings)

    mock_instance.initialize.assert_called_once()
    mock_instance.get_reliable_nodes.assert_called_once_with(
        min_score=mock_args.min_score,
        limit=mock_args.limit,
        days_active=mock_args.days_active,
    )
    mock_instance.close.assert_called_once()

    captured = capsys.readouterr()
    assert "Top 1 reliable nodes" in captured.out
    assert "test://1.1.1.1:1234" in captured.out


@patch("configstream.commands.HistoricalManager", autospec=True)
def test_handle_history_no_db(mock_manager, mock_args, mock_settings, fs, capsys):
    """Test history command when database does not exist."""
    handle_history(mock_args, mock_settings)
    captured = capsys.readouterr()
    assert "History database not found" in captured.out
    mock_manager.assert_not_called()


@patch("configstream.metrics.prometheus_exporter.start_exporter")
def test_handle_prometheus(mock_start_exporter, mock_args, mock_settings):
    """Test the prometheus command handler."""
    mock_args.port = 9090
    handle_prometheus(mock_args, mock_settings)
    mock_start_exporter.assert_called_once_with(
        Path(mock_settings.output.output_dir), mock_args.port
    )
