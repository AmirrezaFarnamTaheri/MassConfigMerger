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
from .core.config_processor import ConfigProcessor
from .core.types import ConfigResult
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
    settings: Settings,
    write_output_files: bool = True,
) -> list[ConfigResult]:
    """
    Run the VPN merger pipeline to test, sort, and merge configurations.

    Args:
        settings: The application settings object.
        write_output_files: Whether to write the final configuration files.

    Returns:
        A list of `ConfigResult` objects representing the tested and sorted nodes.
    """
    source_manager = SourceManager(settings)
    config_processor = ConfigProcessor(settings)
    output_generator = OutputGenerator(settings)
    db = Database(settings.output.history_db_file)
    await db.connect()

    sources_file = Path(settings.sources.sources_file)
    resume_file = Path(settings.processing.resume_file) if settings.processing.resume_file else None

    try:
        configs = await _load_configs(source_manager, sources_file, resume_file)
        history = await db.get_proxy_history()
        filtered_configs = config_processor.filter_configs(configs)

        results = await pipeline.test_configs(list(filtered_configs), settings, history, db)
        sorted_results = pipeline.sort_and_trim_results(results, settings)

        if write_output_files:
            final_configs = [r.config for r in sorted_results]
            output_dir = Path(settings.output.output_dir)
            output_generator.write_outputs(final_configs, output_dir)

        return sorted_results

    finally:
        await source_manager.close_session()
        await db.close()
