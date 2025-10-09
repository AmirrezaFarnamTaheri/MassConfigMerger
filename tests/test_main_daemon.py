import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from configstream.main_daemon import ConfigStreamDaemon, main
from configstream.config import Settings


@pytest.fixture
def mock_settings():
    """Fixture for mock Settings object."""
    return MagicMock(spec=Settings)


@pytest.mark.asyncio
async def test_daemon_start_and_shutdown(mock_settings):
    """Test the start and graceful shutdown of the daemon."""
    with patch("configstream.main_daemon.TestScheduler") as MockScheduler, patch(
        "configstream.main_daemon.run_dashboard", new_callable=AsyncMock
    ) as mock_run_dashboard:
        # Arrange
        mock_scheduler_instance = MockScheduler.return_value
        daemon = ConfigStreamDaemon(settings=mock_settings, data_dir=MagicMock())

        async def set_shutdown_event():
            # This task will run in the background and set the shutdown event
            # after a small delay, allowing the daemon to start.
            await asyncio.sleep(0.1)
            daemon.shutdown_event.set()

        # Act
        shutdown_task = asyncio.create_task(set_shutdown_event())
        await daemon.start(interval_hours=1, web_port=9000)
        await shutdown_task  # Ensure the shutdown task completes

        # Assert
        MockScheduler.assert_called_once_with(mock_settings, daemon.data_dir)
        mock_scheduler_instance.start.assert_called_once_with(1)
        mock_run_dashboard.assert_awaited_once_with(port=9000)
        mock_scheduler_instance.stop.assert_called_once()


@pytest.mark.asyncio
async def test_daemon_signal_handler(mock_settings):
    """Test that the signal handler sets the shutdown event."""
    daemon = ConfigStreamDaemon(settings=mock_settings, data_dir=MagicMock())
    assert not daemon.shutdown_event.is_set()

    daemon._signal_handler()

    assert daemon.shutdown_event.is_set()


@patch("configstream.main_daemon.ConfigStreamDaemon")
@patch("configstream.main_daemon.Settings")
@patch("configstream.main_daemon.Path")
@patch("asyncio.get_event_loop")
def test_main_function(mock_get_loop, mock_path, mock_settings_cls, mock_daemon_cls):
    """Test the main entry point of the daemon."""
    # Arrange
    mock_loop = MagicMock()
    mock_get_loop.return_value = mock_loop
    mock_daemon_instance = mock_daemon_cls.return_value
    mock_loop.run_until_complete.side_effect = lambda x: asyncio.run(
        asyncio.sleep(0.01)
    )  # Simulate running

    # Act
    main()

    # Assert
    mock_settings_cls.assert_called_once()
    mock_path.assert_called_with("./data")
    mock_path.return_value.mkdir.assert_called_once_with(exist_ok=True)
    mock_daemon_cls.assert_called_once()

    # Verify that start was called on the instance
    mock_daemon_instance.start.assert_called_once_with(interval_hours=2, web_port=8080)

    # Verify signal handlers were added
    assert mock_loop.add_signal_handler.call_count > 0
    mock_loop.close.assert_called_once()


@patch("configstream.main_daemon.ConfigStreamDaemon")
@patch("configstream.main_daemon.Settings")
@patch("configstream.main_daemon.Path")
@patch("asyncio.get_event_loop")
def test_main_function_loop_exception(
    mock_get_loop, mock_path, mock_settings_cls, mock_daemon_cls
):
    """Test that the loop is closed even if an exception occurs."""
    mock_loop = MagicMock()
    mock_get_loop.return_value = mock_loop
    mock_loop.run_until_complete.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        main()

    mock_loop.close.assert_called_once()