import pytest
from unittest.mock import patch, MagicMock
import signal
import asyncio

from configstream.main_daemon import ConfigStreamDaemon, main
from configstream.config import Settings


@pytest.fixture
def mock_settings():
    """Fixture for a mock Settings object."""
    return Settings()


@pytest.mark.asyncio
async def test_daemon_start(mock_settings, tmp_path):
    """Test the start method of the daemon."""
    with patch("configstream.main_daemon.TestScheduler") as MockScheduler, \
         patch("configstream.main_daemon.run_dashboard") as mock_run_dashboard, \
         patch("signal.signal") as mock_signal:

        mock_scheduler_instance = MockScheduler.return_value
        mock_run_dashboard.side_effect = lambda **kwargs: None

        daemon = ConfigStreamDaemon(settings=mock_settings, data_dir=tmp_path)
        daemon.start(interval_hours=1, web_port=9000)

        MockScheduler.assert_called_once_with(mock_settings, tmp_path)
        mock_scheduler_instance.start.assert_called_once_with(1)
        mock_run_dashboard.assert_called_once_with(host='0.0.0.0', port=9000)

        # Check that signal handlers were set
        assert mock_signal.call_count == 2
        mock_signal.assert_any_call(signal.SIGINT, daemon._signal_handler)
        mock_signal.assert_any_call(signal.SIGTERM, daemon._signal_handler)


def test_daemon_signal_handler(mock_settings, tmp_path):
    """Test the signal handler of the daemon."""
    daemon = ConfigStreamDaemon(settings=mock_settings, data_dir=tmp_path)

    with patch.object(daemon.scheduler, "stop") as mock_stop, \
         patch("sys.exit") as mock_exit:

        daemon._signal_handler(signal.SIGINT, None)

        mock_stop.assert_called_once()
        assert daemon.running is False
        mock_exit.assert_called_once_with(0)


@patch("configstream.main_daemon.ConfigStreamDaemon")
@patch("configstream.main_daemon.Settings")
@patch("configstream.main_daemon.Path")
def test_main_function(mock_path_cls, mock_settings_cls, mock_daemon_cls):
    """Test the main entry point of the daemon."""
    mock_daemon_instance = mock_daemon_cls.return_value

    main()

    mock_path_cls.assert_called_with("./data")
    mock_path_cls.return_value.mkdir.assert_called_once_with(exist_ok=True)
    mock_daemon_cls.assert_called_once()
    mock_daemon_instance.start.assert_called_once_with(interval_hours=2, web_port=8080)