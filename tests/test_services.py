from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from configstream import services
from configstream.config import Settings
from configstream.exceptions import ConfigError


def test_list_sources_no_file(capsys):
    """Test list_sources when the sources file doesn't exist."""
    services.list_sources(Path("nonexistent.txt"))
    captured = capsys.readouterr()
    assert "No sources found." in captured.out


def test_list_sources_empty_file(fs, capsys):
    """Test list_sources with an empty sources file."""
    fs.create_file("sources.txt")
    services.list_sources(Path("sources.txt"))
    captured = capsys.readouterr()
    assert "No sources found." in captured.out


def test_list_sources_with_content(fs, capsys):
    """Test list_sources with a file containing sources."""
    fs.create_file(
        "sources.txt", contents="http://source1.com\nhttp://source2.com\n")
    services.list_sources(Path("sources.txt"))
    captured = capsys.readouterr()
    assert "1. http://source1.com" in captured.out
    assert "2. http://source2.com" in captured.out


def test_add_new_source(fs, capsys):
    """Test adding a new source."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    services.add_new_source(sources_file, "http://newsource.com")
    captured = capsys.readouterr()
    assert "Successfully added source: http://newsource.com" in captured.out
    assert sources_file.read_text() == "http://newsource.com\n"


def test_add_existing_source(fs, capsys):
    """Test adding a source that already exists."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://newsource.com\n")
    services.add_new_source(sources_file, "http://newsource.com")
    captured = capsys.readouterr()
    assert "Source already exists: http://newsource.com" in captured.out
    assert sources_file.read_text() == "http://newsource.com\n"


def test_add_invalid_source(fs, capsys):
    """Test adding an invalid source URL."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file)
    services.add_new_source(sources_file, "http://")
    captured = capsys.readouterr()
    assert "Error: Invalid URL format: http://" in captured.out


def test_remove_existing_source(fs, capsys):
    """Test removing an existing source."""
    sources_file = Path("sources.txt")
    fs.create_file(
        sources_file, contents="http://source1.com\nhttp://source2.com\n")
    services.remove_existing_source(sources_file, "http://source1.com")
    captured = capsys.readouterr()
    assert "Successfully removed source: http://source1.com" in captured.out
    assert sources_file.read_text() == "http://source2.com\n"


def test_remove_nonexistent_source(fs, capsys):
    """Test removing a source that does not exist."""
    sources_file = Path("sources.txt")
    fs.create_file(sources_file, contents="http://source1.com\n")
    services.remove_existing_source(sources_file, "http://nonexistent.com")
    captured = capsys.readouterr()
    assert "Source not found: http://nonexistent.com" in captured.out
    assert sources_file.read_text() == "http://source1.com\n"


@pytest.mark.asyncio
@patch("configstream.pipeline.run_aggregation_pipeline", new_callable=AsyncMock)
async def test_run_fetch_pipeline(mock_run_agg_pipeline):
    """Test the run_fetch_pipeline service."""
    settings = Settings()
    await services.run_fetch_pipeline(
        settings, Path("s.txt"), Path("c.txt"), 12, 5, False
    )
    mock_run_agg_pipeline.assert_awaited_once_with(
        settings,
        sources_file=Path("s.txt"),
        channels_file=Path("c.txt"),
        last_hours=12,
        failure_threshold=5,
        prune=False,
    )


@pytest.mark.asyncio
@patch("configstream.vpn_merger.run_merger", new_callable=AsyncMock)
async def test_run_merge_pipeline(mock_run_merger):
    """Test the run_merge_pipeline service."""
    settings = Settings()
    await services.run_merge_pipeline(settings, Path("s.txt"), Path("r.txt"))
    mock_run_merger.assert_awaited_once_with(
        settings, sources_file=Path("s.txt"), resume_file=Path("r.txt")
    )


@pytest.mark.asyncio
@patch("configstream.vpn_retester.run_retester", new_callable=AsyncMock)
async def test_run_retest_pipeline(mock_run_retester):
    """Test the run_retest_pipeline service."""
    settings = Settings()
    await services.run_retest_pipeline(settings, Path("i.txt"))
    mock_run_retester.assert_awaited_once_with(
        settings, input_file=Path("i.txt"))


@pytest.mark.asyncio
@patch("configstream.pipeline.run_aggregation_pipeline", new_callable=AsyncMock)
@patch("configstream.vpn_merger.run_merger", new_callable=AsyncMock)
async def test_run_full_pipeline(mock_run_merger, mock_run_agg_pipeline):
    """Test the run_full_pipeline service."""
    mock_run_agg_pipeline.return_value = (Path("output"), [])
    settings = Settings()
    await services.run_full_pipeline(
        settings, Path("s.txt"), Path("c.txt"), 12, 5, True
    )
    mock_run_agg_pipeline.assert_awaited_once()
    mock_run_merger.assert_awaited_once()
