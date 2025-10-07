import asyncio
from unittest.mock import MagicMock

from configstream import get_client_loop


def test_get_client_loop_success():
    """Test that the event loop is returned correctly when get_loop exists."""
    mock_loop = asyncio.new_event_loop()
    mock_session = MagicMock()
    mock_session.get_loop.return_value = mock_loop

    assert get_client_loop(mock_session) is mock_loop
    mock_session.get_loop.assert_called_once()


def test_get_client_loop_runtime_error():
    """Test that None is returned when get_loop raises a RuntimeError."""
    mock_session = MagicMock()
    mock_session.get_loop.side_effect = RuntimeError

    assert get_client_loop(mock_session) is None
    mock_session.get_loop.assert_called_once()


def test_get_client_loop_fallback_to_loop_attribute():
    """Test that the _loop attribute is returned when get_loop is not available."""
    mock_loop = asyncio.new_event_loop()
    mock_session = MagicMock(spec=["_loop"])  # Does not have get_loop
    mock_session._loop = mock_loop

    assert get_client_loop(mock_session) is mock_loop


def test_get_client_loop_no_loop_available():
    """Test that None is returned when no loop can be found."""
    mock_session = MagicMock(spec=[])  # Has no methods or attributes

    assert get_client_loop(mock_session) is None