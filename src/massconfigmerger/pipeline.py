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
from typing import Set

from .config import Settings
from .constants import CHANNELS_FILE, SOURCES_FILE
from .core.config_processor import ConfigProcessor
from .core.output_generator import OutputGenerator
from .core.source_manager import SourceManager
from .telegram_scraper import scrape_telegram_configs


async def _fetch_web_sources(
    source_manager: SourceManager,
    sources_file: Path,
    *,
    failure_threshold: int,
    prune: bool,
) -> Set[str]:
    """Fetch configurations from web sources."""
    logging.info("Fetching configurations from web sources...")
    available_sources = await source_manager.check_and_update_sources(
        sources_file, max_failures=failure_threshold, prune=prune
    )
    configs = await source_manager.fetch_sources(available_sources)
    logging.info("Found %d configs from %d web sources.", len(configs), len(available_sources))
    return configs


async def _scrape_telegram_sources(
    cfg: Settings, channels_file: Path, last_hours: int
) -> Set[str]:
    """Scrape configurations from Telegram channels."""
    if not (channels_file and channels_file.exists()):
        logging.info("Telegram channels file not found, skipping scrape.")
        return set()

    logging.info("Scraping configurations from Telegram channels...")
    configs = await scrape_telegram_configs(cfg, channels_file, last_hours)
    logging.info("Found %d configs from Telegram.", len(configs))
    return configs


async def run_aggregation_pipeline(
    cfg: Settings,
    sources_file: Path = SOURCES_FILE,
    channels_file: Path = CHANNELS_FILE,
    last_hours: int = 24,
    *,
    failure_threshold: int = 3,
    prune: bool = True,
) -> tuple[Path, list[Path]]:
    """Run the full aggregation pipeline to fetch and process configurations."""
    source_manager = SourceManager(cfg)
    config_processor = ConfigProcessor(cfg)
    output_generator = OutputGenerator(cfg)
    all_configs: Set[str] = set()

    try:
        web_configs = await _fetch_web_sources(
            source_manager,
            sources_file,
            failure_threshold=failure_threshold,
            prune=prune,
        )
        all_configs.update(web_configs)

        telegram_configs = await _scrape_telegram_sources(
            cfg, channels_file, last_hours
        )
        all_configs.update(telegram_configs)

        # Filter and process configs
        filtered_configs = config_processor.filter_configs(
            all_configs, use_fetch_rules=True
        )
        sorted_configs = sorted(list(filtered_configs))

        # Write output files
        output_dir = cfg.output.output_dir
        files = output_generator.write_outputs(sorted_configs, output_dir)

        logging.info(
            "Aggregation complete. Found %d final configs.", len(sorted_configs)
        )
        return output_dir, files

    finally:
        await source_manager.close_session()
