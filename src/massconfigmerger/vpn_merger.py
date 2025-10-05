"""Core logic for the VPN merger pipeline.

This module contains the `run_merger` function, which serves as the primary
orchestrator for the 'merge' operation. It handles fetching configurations
from sources (or resuming from a file), testing their connectivity, sorting
them by performance, and writing the final results to various output files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .config import Settings
from .core.config_processor import ConfigProcessor
from .core.output_generator import OutputGenerator
from .core.source_manager import SourceManager
from .core.utils import get_sort_key
from .db import Database


async def run_merger(
    cfg: Settings,
    sources_file: Path,
    resume_file: Optional[Path] = None,
) -> None:
    """
    Run the VPN merger pipeline to test, sort, and merge configurations.

    This function orchestrates the entire merge process, which includes:
    1.  Loading configurations, either by fetching from web sources defined
        in `sources_file` or by resuming from a local `resume_file`.
    2.  Filtering the configurations based on the merge-stage protocol rules.
    3.  Testing each configuration for connectivity and latency.
    4.  Sorting the results based on the configured metric (e.g., latency).
    5.  Optionally trimming the list to the top N results.
    6.  Writing the final configurations to all configured output formats.

    Args:
        cfg: The application settings object.
        sources_file: The path to the file containing web source URLs. This is
                      used if `resume_file` is not provided.
        resume_file: An optional path to a raw or base64-encoded subscription
                     file to re-test and merge, instead of fetching from sources.
    """
    source_manager = SourceManager(cfg)
    config_processor = ConfigProcessor(cfg)
    output_generator = OutputGenerator(cfg)
    db = Database(cfg.output.history_db_file)
    await db.connect()

    try:
        if resume_file:
            with resume_file.open() as f:
                configs = {line.strip() for line in f if line.strip()}
        else:
            with sources_file.open() as f:
                sources = [line.strip() for line in f if line.strip()]
            configs = await source_manager.fetch_sources(sources)

        history = await db.get_proxy_history()
        filtered_configs = config_processor.filter_configs(configs)
        results = await config_processor.test_configs(filtered_configs, history)

        if cfg.processing.enable_sorting:
            results.sort(key=get_sort_key(cfg.processing.sort_by))

        if cfg.processing.top_n > 0:
            results = results[: cfg.processing.top_n]

        # Update history
        for result in results:
            if result.host and result.port:
                key = f"{result.host}:{result.port}"
                await db.update_proxy_history(key, result.is_reachable)

        final_configs = [r.config for r in results]
        output_dir = Path(cfg.output.output_dir)
        output_generator.write_outputs(final_configs, output_dir)

        logging.info("Merge complete. Found %d configs.", len(final_configs))

    finally:
        await source_manager.close_session()
        await db.close()
