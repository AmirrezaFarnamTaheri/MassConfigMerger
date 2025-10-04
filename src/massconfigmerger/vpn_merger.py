"""VPN Subscription Merger.

This module provides a command line tool to merge and test VPN configurations
from various sources.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from .config import Settings
from .core.config_processor import ConfigProcessor
from .core.output_generator import OutputGenerator
from .core.source_manager import SourceManager


async def run_merger(
    cfg: Settings,
    sources_file: Path,
    protocols: Optional[List[str]] = None,
    resume_file: Optional[Path] = None,
    sort: bool = True,
    top_n: int = 0,
) -> None:
    """
    Run the VPN merger pipeline.

    Args:
        cfg: The application settings.
        sources_file: The path to the sources file.
        protocols: A list of protocols to include.
        resume_file: A file to resume from.
        sort: Whether to sort the results by latency.
        top_n: The number of top results to keep.
    """
    source_manager = SourceManager(cfg)
    config_processor = ConfigProcessor(cfg)
    output_generator = OutputGenerator(cfg)

    try:
        if resume_file:
            with resume_file.open() as f:
                configs = {line.strip() for line in f if line.strip()}
        else:
            with sources_file.open() as f:
                sources = [line.strip() for line in f if line.strip()]
            configs = await source_manager.fetch_sources(sources)

        filtered_configs = config_processor.filter_configs(configs, protocols)
        results = await config_processor.test_configs(filtered_configs)

        if sort:
            results.sort(
                key=lambda x: (x[1] is None, x[1] if x[1] is not None else float("inf"))
            )

        if top_n > 0:
            results = results[:top_n]

        final_configs = [c for c, _ in results]
        output_dir = Path(cfg.output.output_dir)
        output_generator.write_outputs(final_configs, output_dir)

        logging.info("Merge complete. Found %d configs.", len(final_configs))

    finally:
        await source_manager.close_session()


# This file is not intended to be run directly anymore.
# The main entry point is now cli.py.