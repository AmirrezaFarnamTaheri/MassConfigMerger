from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.config import Settings
from configstream.pipeline import run_aggregation_pipeline


@pytest.mark.asyncio
@patch("configstream.pipeline.SourceManager")
@patch("configstream.pipeline.ConfigProcessor")
@patch("configstream.pipeline.OutputGenerator")
@patch("configstream.pipeline.scrape_telegram_configs", new_callable=AsyncMock)
async def test_run_aggregation_pipeline_full_flow(
    mock_scrape_telegram: AsyncMock,
    MockOutputGenerator: MagicMock,
    MockConfigProcessor: MagicMock,
    MockSourceManager: MagicMock,
    tmp_path: Path,
):
    """Test the full flow of the aggregation pipeline, including Telegram scraping."""
    # Arrange
    settings = Settings()
    settings.output.output_dir = tmp_path

    # Mock instances and their methods
    mock_source_manager = MockSourceManager.return_value
    mock_config_processor = MockConfigProcessor.return_value
    mock_output_generator = MockOutputGenerator.return_value

    mock_source_manager.check_and_update_sources = AsyncMock(return_value=["http://source1"])
    mock_source_manager.fetch_sources = AsyncMock(return_value={"vless://config1"})
    mock_scrape_telegram.return_value = {"ss://config2"}
    mock_config_processor.filter_configs.return_value = {"vless://config1", "ss://config2"}
    mock_output_generator.write_outputs.return_value = [tmp_path / "file1.txt"]
    mock_source_manager.close_session = AsyncMock()

    sources_file = tmp_path / "sources.txt"
    channels_file = tmp_path / "channels.txt"
    sources_file.touch()
    channels_file.touch()

    # Act
    output_dir, written_files = await run_aggregation_pipeline(
        settings,
        sources_file=sources_file,
        channels_file=channels_file,
        last_hours=12,
        failure_threshold=5,
        prune=False,
    )

    # Assert
    mock_source_manager.check_and_update_sources.assert_awaited_once_with(
        sources_file, max_failures=5, prune=False
    )
    mock_source_manager.fetch_sources.assert_awaited_once_with(["http://source1"])
    mock_scrape_telegram.assert_awaited_once_with(settings, channels_file, 12)
    mock_config_processor.filter_configs.assert_called_once_with(
        {"vless://config1", "ss://config2"}, use_fetch_rules=True
    )
    mock_output_generator.write_outputs.assert_called_once_with(
        sorted(["vless://config1", "ss://config2"]), tmp_path
    )
    mock_source_manager.close_session.assert_awaited_once()

    assert output_dir == tmp_path
    assert written_files == [tmp_path / "file1.txt"]


@pytest.mark.asyncio
@patch("configstream.pipeline.SourceManager")
@patch("configstream.pipeline.ConfigProcessor")
@patch("configstream.pipeline.OutputGenerator")
@patch("configstream.pipeline.scrape_telegram_configs", new_callable=AsyncMock)
async def test_run_aggregation_pipeline_no_telegram(
    mock_scrape_telegram: AsyncMock,
    MockOutputGenerator: MagicMock,
    MockConfigProcessor: MagicMock,
    MockSourceManager: MagicMock,
    tmp_path: Path,
):
    """Test the pipeline flow when no channels file is provided."""
    # Arrange
    settings = Settings()
    mock_source_manager = MockSourceManager.return_value
    mock_source_manager.check_and_update_sources = AsyncMock(return_value=[])
    mock_source_manager.fetch_sources = AsyncMock(return_value={"vless://config1"})
    mock_source_manager.close_session = AsyncMock()

    # Act
    await run_aggregation_pipeline(settings, channels_file=None)

    # Assert
    mock_scrape_telegram.assert_not_called()
    mock_source_manager.close_session.assert_awaited_once()