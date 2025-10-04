"""Main pipeline for aggregating and processing configurations.

This module provides the primary `run_aggregation_pipeline` function, which
orchestrates the entire process of fetching, filtering, and writing
configurations from various sources.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Set

from .config import Settings
from .constants import SOURCES_FILE, CHANNELS_FILE
from .core.config_processor import ConfigProcessor
from .core.output_generator import OutputGenerator
from .core.source_manager import SourceManager
from .telegram_scraper import scrape_telegram_configs


async def run_aggregation_pipeline(
    cfg: Settings,
    protocols: Optional[List[str]] = None,
    sources_file: Path = SOURCES_FILE,
    channels_file: Path = CHANNELS_FILE,
    last_hours: int = 24,
    *,
    failure_threshold: int = 3,
    prune: bool = True,
) -> tuple[Path, list[Path]]:
    """
    Run the full aggregation pipeline.

    This involves fetching configs from web sources and Telegram,
    filtering them, and writing the results to output files.

    Args:
        cfg: The application settings.
        protocols: A list of protocols to filter for.
        sources_file: Path to the file containing web sources.
        channels_file: Path to the file containing Telegram channels.
        last_hours: How many hours of Telegram history to scan.
        failure_threshold: Max failures before a web source is pruned.
        prune: Whether to remove failing web sources.

    Returns:
        A tuple containing the output directory path and a list of
        paths to the files that were written.
    """
    source_manager = SourceManager(cfg)
    config_processor = ConfigProcessor(cfg)
    output_generator = OutputGenerator(cfg)

    try:
        # Fetch configs from web sources
        available_sources = await source_manager.check_and_update_sources(
            sources_file, max_failures=failure_threshold, prune=prune
        )
        configs: Set[str] = await source_manager.fetch_sources(available_sources)

        # Scrape configs from Telegram if a channels file is provided
        if channels_file:
            telegram_configs = await scrape_telegram_configs(
                cfg, channels_file, last_hours
            )
            configs.update(telegram_configs)

        # Filter and process configs
        filtered_configs = config_processor.filter_configs(configs, protocols)
        sorted_configs = sorted(list(filtered_configs))

        # Write output files
        output_dir = Path(cfg.output.output_dir)
        files = output_generator.write_outputs(sorted_configs, output_dir)

        logging.info("Aggregation complete. Found %d configs.", len(sorted_configs))
        return output_dir, files

    finally:
        await source_manager.close_session()