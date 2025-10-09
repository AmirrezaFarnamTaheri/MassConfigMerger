import pytest
from unittest.mock import patch, AsyncMock
from pathlib import Path
import json
import time
import asyncio

from configstream.core.source_manager import SourceManager
from configstream.config import Settings
from configstream.exceptions import NetworkError


@pytest.mark.asyncio
async def test_fetch_sources_network_error():
    """Test fetch_sources when a NetworkError occurs."""
    settings = Settings()
    manager = SourceManager(settings)
    source_url = "http://example.com/source"

    with patch("configstream.core.utils.fetch_text", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = NetworkError("HTTP 404")
        results = await manager.fetch_sources([source_url])
        assert results == set()
        await manager.close_session()


@pytest.mark.asyncio
async def test_check_and_update_sources_no_file():
    """Test check_and_update_sources when the sources file doesn't exist."""
    settings = Settings()
    manager = SourceManager(settings)
    sources = await manager.check_and_update_sources(Path("/nonexistent/sources.txt"))
    assert sources == []
    await manager.close_session()


@pytest.mark.asyncio
async def test_unhandled_exception_in_check(tmp_path):
    """Test that an unhandled exception during check is caught."""
    settings = Settings()
    manager = SourceManager(settings)
    sources_path = tmp_path / "sources.txt"
    sources_path.write_text("http://test.com\n")

    with patch("configstream.core.utils.fetch_text", side_effect=Exception("Unhandled")):
        valid_sources = await manager.check_and_update_sources(sources_path)
        assert valid_sources == []
    await manager.close_session()


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_recovers():
    """Test the full circuit breaker logic: OPEN -> HALF_OPEN -> CLOSED."""
    settings = Settings()
    manager = SourceManager(settings)
    manager.RETRY_TIMEOUT = 0.1 # Shorten for test
    source_url = "http://fails.com"

    with patch("configstream.core.utils.fetch_text", new_callable=AsyncMock) as mock_fetch, \
         patch("configstream.core.source_manager.tqdm", side_effect=lambda x, **kw: x):
        # 1. Fail 3 times to open the circuit
        mock_fetch.side_effect = NetworkError("Fail")
        for _ in range(3):
            await manager.fetch_sources([source_url])

        assert manager._circuit_states.get(source_url) == "OPEN"

        # 2. Fetching again should skip because circuit is open
        mock_fetch.reset_mock()
        await manager.fetch_sources([source_url])
        mock_fetch.assert_not_called()

        # 3. Wait for retry timeout and enter HALF_OPEN state
        time.sleep(0.2)

        # 4. Succeed once to close the circuit
        mock_fetch.side_effect = None
        mock_fetch.return_value = "vless://config"
        await manager.fetch_sources([source_url])

        mock_fetch.assert_called_once()
        assert source_url not in manager._circuit_states

    await manager.close_session()


@pytest.mark.asyncio
async def test_session_recreation():
    """Test that the aiohttp session is recreated after being closed."""
    settings = Settings()
    manager = SourceManager(settings)

    session1 = await manager.get_session()
    assert not session1.closed

    await manager.close_session()
    assert session1.closed

    session2 = await manager.get_session()
    assert not session2.closed
    assert session1 is not session2

    await manager.close_session()


@pytest.mark.asyncio
async def test_fetch_sources_no_tasks():
    """Test fetch_sources with no safe sources to create tasks."""
    settings = Settings()
    manager = SourceManager(settings)
    results = await manager.fetch_sources(["ftp://example.com"])
    assert results == set()
    await manager.close_session()


@pytest.mark.asyncio
async def test_check_and_update_sources_no_tasks(tmp_path):
    """Test check_and_update_sources with no safe sources."""
    settings = Settings()
    manager = SourceManager(settings)
    sources_path = tmp_path / "sources.txt"
    sources_path.write_text("ftp://example.com\n")
    results = await manager.check_and_update_sources(sources_path)
    assert results == []
    await manager.close_session()

@pytest.mark.asyncio
async def test_check_and_update_cancelled_task(tmp_path):
    """Test that cancelled tasks in check_and_update are handled."""
    settings = Settings()
    manager = SourceManager(settings)
    sources_path = tmp_path / "sources.txt"
    sources_path.write_text("http://test.com\n")

    async def cancel_after_start(session, url, **kwargs):
        # This will be cancelled by the test logic
        await asyncio.sleep(1)

    with patch("configstream.core.utils.fetch_text", side_effect=cancel_after_start):
        # We expect the check to be cancelled, but not to raise an error
        await manager.check_and_update_sources(sources_path)

    await manager.close_session()