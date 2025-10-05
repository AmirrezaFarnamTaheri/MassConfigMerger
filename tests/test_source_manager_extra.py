from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from massconfigmerger.config import Settings
from massconfigmerger.core.source_manager import SourceManager


@pytest.mark.asyncio
@patch("massconfigmerger.core.utils.fetch_text")
async def test_check_and_update_sources_failure_counting(mock_fetch_text: AsyncMock, fs):
    """Test that check_and_update_sources correctly counts failures."""
    # Arrange
    mock_fetch_text.return_value = None  # Simulate all sources failing
    settings = Settings()
    source_manager = SourceManager(settings)
    sources_path = Path("sources.txt")
    failures_path = sources_path.with_suffix(".failures.json")

    sources = ["http://bad.com/sub1", "http://bad.com/sub2"]
    fs.create_file(sources_path, contents="\n".join(sources))
    fs.create_file(failures_path, contents='{"http://bad.com/sub1": 1}')

    # Act
    valid_sources = await source_manager.check_and_update_sources(
        sources_path, max_failures=3, prune=False
    )

    # Assert
    assert not valid_sources
    failures_data = json.loads(failures_path.read_text())
    assert failures_data.get("http://bad.com/sub1") == 2
    assert failures_data.get("http://bad.com/sub2") == 1


@pytest.mark.asyncio
@patch("massconfigmerger.core.utils.fetch_text")
async def test_check_and_update_sources_pruning(mock_fetch_text: AsyncMock, fs):
    """Test that failing sources are correctly pruned."""
    # Arrange
    # Good source returns content with configs, bad source returns None
    async def fetch_side_effect(session, url, **kwargs):
        if "good.com" in url:
            return "vless://good"
        return None
    mock_fetch_text.side_effect = fetch_side_effect

    settings = Settings()
    source_manager = SourceManager(settings)
    sources_path = Path("sources.txt")
    failures_path = sources_path.with_suffix(".failures.json")
    disabled_path = sources_path.with_name("sources_disabled.txt")

    sources = ["http://good.com/sub", "http://bad.com/sub"]
    fs.create_file(sources_path, contents="\n".join(sources))
    # Pre-existing failures for bad.com, enough to trigger pruning
    fs.create_file(failures_path, contents='{"http://bad.com/sub": 2}')

    # Act
    valid_sources = await source_manager.check_and_update_sources(
        sources_path, max_failures=3, prune=True
    )

    # Assert
    assert valid_sources == ["http://good.com/sub"]
    assert sources_path.read_text().strip() == "http://good.com/sub"
    assert disabled_path.read_text().strip() == "http://bad.com/sub"
    # The failure should be removed from the failures file after pruning
    failures_data = json.loads(failures_path.read_text())
    assert "http://bad.com/sub" not in failures_data


@pytest.mark.asyncio
@patch("massconfigmerger.core.utils.fetch_text", return_value="vless://config")
async def test_check_and_update_sources_invalid_failures_json(mock_fetch_text, fs):
    """Test that check_and_update_sources handles invalid failures.json gracefully."""
    settings = Settings()
    source_manager = SourceManager(settings)
    sources_path = Path("sources.txt")
    failures_path = sources_path.with_suffix(".failures.json")

    fs.create_file(sources_path, contents="http://example.com/sub")
    fs.create_file(failures_path, contents="{invalid json")

    await source_manager.check_and_update_sources(sources_path)

    # Should be empty because the file was invalid, and the source succeeded.
    failures_data = json.loads(failures_path.read_text())
    assert failures_data == {}


@pytest.mark.asyncio
async def test_close_session_logic():
    """Test the close_session logic for various states."""
    settings = Settings()

    # Scenario 1: Session does not exist
    source_manager = SourceManager(settings)
    await source_manager.close_session() # Should not raise

    # Scenario 2: Session is already closed
    source_manager = SourceManager(settings)
    mock_session = AsyncMock()
    mock_session.closed = True
    source_manager.session = mock_session
    await source_manager.close_session()
    mock_session.close.assert_not_called()

    # Scenario 3: Session is open and should be closed
    source_manager = SourceManager(settings)
    mock_session = AsyncMock()
    mock_session.closed = False
    mock_session.close = AsyncMock()
    source_manager.session = mock_session
    await source_manager.close_session()
    mock_session.close.assert_awaited_once()