from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from configstream.config import Settings
from configstream.core.source_manager import SourceManager
from configstream.exceptions import NetworkError


@pytest.mark.asyncio
async def test_fetch_sources_circuit_breaker(fs):
    """Test that the circuit breaker opens after repeated failures."""
    sources_file = Path("sources.txt")
    sources_file.write_text("http://fails.com\n")
    settings = Settings()
    manager = SourceManager(settings)
    manager.FAILURE_THRESHOLD = 2

    with patch("configstream.core.utils.fetch_text", new_callable=AsyncMock) as mock_fetch:
        # First 2 calls should fail, opening the circuit
        mock_fetch.side_effect = NetworkError("Failed to fetch")
        await manager.fetch_sources(["http://fails.com"])
        await manager.fetch_sources(["http://fails.com"])

        # The third call should not even attempt to fetch
        await manager.fetch_sources(["http://fails.com"])
        assert mock_fetch.call_count == 2
        assert manager._circuit_states["http://fails.com"] == "OPEN"

    await manager.close_session()


@pytest.mark.asyncio
async def test_check_and_update_sources_no_prune(fs):
    """Test check_and_update_sources with pruning disabled."""
    sources_file = Path("sources.txt")
    sources_file.write_text("http://fails.com\n")
    failures_file = sources_file.with_suffix(".failures.json")
    disabled_file = sources_file.with_name("sources_disabled.txt")

    settings = Settings()
    manager = SourceManager(settings)

    with patch("configstream.core.utils.fetch_text", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = NetworkError("Failed to fetch")
        valid_sources = await manager.check_and_update_sources(
            sources_file, max_failures=1, prune=False
        )

    assert not valid_sources
    assert "http://fails.com" in failures_file.read_text()
    assert not disabled_file.exists()  # Should not be created
    assert sources_file.read_text() == "http://fails.com\n"  # Should not be modified

    await manager.close_session()




@pytest.mark.asyncio
async def test_circuit_breaker_half_open_success(fs):
    """Test that a HALF_OPEN circuit closes on success."""
    settings = Settings()
    manager = SourceManager(settings)
    url = "http://half-open.com"
    manager._circuit_states[url] = "HALF_OPEN"
    manager._failure_counts[url] = manager.FAILURE_THRESHOLD

    with patch("configstream.core.utils.fetch_text", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "vless://config"
        await manager.fetch_sources([url])
        assert url not in manager._circuit_states
        assert url not in manager._failure_counts

    await manager.close_session()


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure(fs):
    """Test that a HALF_OPEN circuit re-opens on failure."""
    settings = Settings()
    manager = SourceManager(settings)
    url = "http://half-open-fails.com"
    manager._circuit_states[url] = "HALF_OPEN"
    manager._failure_counts[url] = manager.FAILURE_THRESHOLD

    with patch("configstream.core.utils.fetch_text", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = NetworkError("Failed again")
        await manager.fetch_sources([url])
        assert manager._circuit_states[url] == "OPEN"
        assert manager._failure_counts[url] == manager.FAILURE_THRESHOLD + 1

    await manager.close_session()


@pytest.mark.asyncio
async def test_check_sources_no_file(fs):
    """Test check_and_update_sources when the sources file does not exist."""
    settings = Settings()
    manager = SourceManager(settings)
    result = await manager.check_and_update_sources(Path("nonexistent.txt"))
    assert result == []
    await manager.close_session()


@pytest.mark.asyncio
async def test_check_sources_invalid_failures_json(fs):
    """Test check_and_update_sources with invalid failures JSON."""
    sources_file = Path("sources.txt")
    sources_file.write_text("http://works.com\n")
    failures_file = sources_file.with_suffix(".failures.json")
    failures_file.write_text("this is not json")

    settings = Settings()
    manager = SourceManager(settings)

    with patch("configstream.core.utils.fetch_text", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "vless://config"
        valid_sources = await manager.check_and_update_sources(sources_file)
        assert valid_sources == ["http://works.com"]

    await manager.close_session()


@pytest.mark.asyncio
async def test_check_and_update_sources_with_prune(fs):
    """Test check_and_update_sources with pruning enabled."""
    sources_file = Path("sources.txt")
    sources_file.write_text("http://fails.com\nhttp://works.com\n")
    failures_file = sources_file.with_suffix(".failures.json")
    disabled_file = sources_file.with_name("sources_disabled.txt")

    settings = Settings()
    manager = SourceManager(settings)

    with patch("configstream.core.utils.fetch_text", new_callable=AsyncMock) as mock_fetch:
        # Let one source fail and the other succeed
        async def fetch_side_effect(session, url, **kwargs):
            if "fails.com" in url:
                raise NetworkError("Failed to fetch")
            return "vless://config"

        mock_fetch.side_effect = fetch_side_effect
        valid_sources = await manager.check_and_update_sources(
            sources_file, max_failures=1, prune=True
        )

    assert valid_sources == ["http://works.com"]
    assert "http://fails.com" not in failures_file.read_text()
    assert "http://fails.com" in disabled_file.read_text()
    assert sources_file.read_text().strip() == "http://works.com"

    await manager.close_session()
