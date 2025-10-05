"""Main pipeline for aggregating VPN configurations from multiple sources.

This module provides the primary `run_aggregation_pipeline` function, which
serves as the orchestrator for the entire 'fetch' operation. It coordinates
the process of fetching configurations from web sources and Telegram channels,
filtering them based on specified protocols, and writing the aggregated
results to various output files.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Set

from .config import Settings
from .constants import CHANNELS_FILE, SOURCES_FILE
from .core.config_processor import ConfigProcessor
from .core.output_generator import OutputGenerator
from .core.source_manager import SourceManager
from .telegram_scraper import scrape_telegram_configs


async def run_aggregation_pipeline(
    cfg: Settings,
    sources_file: Path = SOURCES_FILE,
    channels_file: Path = CHANNELS_FILE,
    last_hours: int = 24,
    *,
    failure_threshold: int = 3,
    prune: bool = True,
) -> tuple[Path, list[Path]]:
    """
    Run the full aggregation pipeline to fetch and process configurations.

    This function coordinates the main steps of the aggregation process:
    1.  Fetches configurations from web sources listed in `sources_file`.
    2.  Optionally prunes failing web sources based on `failure_threshold`.
    3.  Scrapes configurations from Telegram channels listed in `channels_file`.
    4.  Filters the combined set of configurations based on the protocols
        specified in the settings.
    5.  Writes the final, sorted list of configurations to output files.

    Args:
        cfg: The application settings object.
        sources_file: The path to the file containing web source URLs.
        channels_file: The path to the file containing Telegram channel names.
        last_hours: The number of recent hours of Telegram history to scan.
        failure_threshold: The maximum number of consecutive failures before a
                           web source is considered for pruning.
        prune: If True, remove failing web sources from the `sources_file`.

    Returns:
        A tuple where the first element is the path to the output directory,
        and the second element is a list of paths to the files that were written.
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
        if channels_file and channels_file.exists():
            telegram_configs = await scrape_telegram_configs(
                cfg, channels_file, last_hours
            )
            configs.update(telegram_configs)

        # Filter and process configs
        filtered_configs = config_processor.filter_configs(
            configs, use_fetch_rules=True
        )
        sorted_configs = sorted(list(filtered_configs))

        # Write output files
        output_dir = Path(cfg.output.output_dir)
        files = output_generator.write_outputs(sorted_configs, output_dir)

        logging.info("Aggregation complete. Found %d configs.", len(sorted_configs))
        return output_dir, files

    finally:
        await source_manager.close_session()