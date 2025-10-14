# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Core logic for the VPN merger pipeline.

This module contains the `run_merger` function, which serves as the primary
orchestrator for the 'merge' operation. It delegates core processing tasks
to the `processing` module.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Set

from .config import Settings
from .core.config_processor import ConfigProcessor, ConfigResult
from .core.output_generator import OutputGenerator
from .core.source_manager import SourceManager
from .db import Database
from .processing import pipeline


async def _load_configs(
    source_manager: SourceManager,
    sources_file: Path,
    resume_file: Optional[Path] = None,
) -> Set[str]:
    """Load configurations from a resume file or fetch from sources."""
    if resume_file:
        logging.info("Resuming from file: %s", resume_file)
        with resume_file.open() as f:
            return {line.strip() for line in f if line.strip()}

    logging.info("Fetching configurations from sources file: %s", sources_file)
    with sources_file.open() as f:
        sources = [line.strip() for line in f if line.strip()]
    return await source_manager.fetch_sources(sources)


async def run_merger(
    cfg: Settings,
    sources_file: Path,
    resume_file: Optional[Path] = None,
    write_output_files: bool = True,
) -> list[ConfigResult]:
    """
    Run the VPN merger pipeline to test, sort, and merge configurations.

    Args:
        cfg: The application settings object.
        sources_file: The path to the file containing web source URLs.
        resume_file: An optional path to a subscription file to re-test.
        write_output_files: Whether to write the final configuration files.

    Returns:
        A list of `ConfigResult` objects representing the tested and sorted nodes.
    """
    source_manager = SourceManager(cfg)
    config_processor = ConfigProcessor(cfg)
    output_generator = OutputGenerator(cfg)
    db = Database(cfg.output.history_db_file)
    await db.connect()

    try:
        configs = await _load_configs(source_manager, sources_file, resume_file)
        history = await db.get_proxy_history()
        filtered_configs = config_processor.filter_configs(configs)

        results = await pipeline.test_configs(list(filtered_configs), cfg, history, db)
        sorted_results = pipeline.sort_and_trim_results(results, cfg)

        if write_output_files:
            final_configs = [r.config for r in sorted_results]
            output_dir = Path(cfg.output.output_dir)
            output_generator.write_outputs(final_configs, output_dir)

        return sorted_results

    finally:
        await source_manager.close_session()
        await db.close()
