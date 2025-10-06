"""Core logic for the VPN merger pipeline.

This module contains the `run_merger` function, which serves as the primary
orchestrator for the 'merge' operation. It handles fetching configurations
from sources (or resuming from a file), testing their connectivity, sorting
them by performance, and writing the final results to various output files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List, Optional, Set

from .config import Settings
from .core.config_processor import ConfigProcessor
from .core.output_generator import OutputGenerator
from .core.source_manager import SourceManager
from .core.utils import get_sort_key
from .db import Database


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


async def _update_proxy_history(db: Database, results: List[Any]) -> None:
    """Update proxy history in the database based on test results."""
    logging.debug("Updating proxy history for %d results.", len(results))
    for result in results:
        if result.host and result.port:
            key = f"{result.host}:{result.port}"
            await db.update_proxy_history(key, result.is_reachable)


def _sort_and_trim_results(results: List[Any], cfg: Settings) -> List[Any]:
    """Sort and trim the list of results based on configuration."""
    if cfg.processing.enable_sorting:
        logging.debug("Sorting results by %s.", cfg.processing.sort_by)
        results.sort(key=get_sort_key(cfg.processing.sort_by))

    if cfg.processing.top_n > 0:
        logging.info("Trimming results to top %d.", cfg.processing.top_n)
        results = results[: cfg.processing.top_n]

    return results


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
        # 1. Load configurations
        configs = await _load_configs(source_manager, sources_file, resume_file)

        # 2. Process and test
        history = await db.get_proxy_history()
        filtered_configs = config_processor.filter_configs(configs)
        results = await config_processor.test_configs(filtered_configs, history)

        # 3. Update proxy history
        await _update_proxy_history(db, results)

        # 4. Sort and trim results
        sorted_results = _sort_and_trim_results(results, cfg)

        # 5. Write final output
        final_configs = [r.config for r in sorted_results]
        output_dir = Path(cfg.output.output_dir)
        output_generator.write_outputs(final_configs, output_dir)

        logging.info("Merge complete. Found %d final configs.", len(final_configs))

    finally:
        await source_manager.close_session()
        await db.close()

# End of file
