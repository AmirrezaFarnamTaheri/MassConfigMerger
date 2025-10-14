"""Core processing pipeline for ConfigStream.

This module contains the core logic for processing, testing, and filtering
VPN configurations. It is designed to be reusable across different commands
like 'merge' and 'retest'.
"""

from __future__ import annotations

import logging
from typing import Any

from ..config import Settings
from ..core.config_processor import ConfigProcessor, ConfigResult
from ..core.utils import get_sort_key
from ..db import Database


def sort_and_trim_results(
    results: list[ConfigResult], cfg: Settings
) -> list[ConfigResult]:
    """Sort and trim the list of results based on configuration."""
    if cfg.processing.enable_sorting:
        logging.debug("Sorting results by %s.", cfg.processing.sort_by)
        results.sort(key=get_sort_key(cfg))

    if cfg.processing.top_n > 0:
        logging.info("Trimming results to top %d.", cfg.processing.top_n)
        results = results[: cfg.processing.top_n]

    return results


async def test_configs(
    configs: list[str], cfg: Settings, history: dict[str, Any], db: Database
) -> list[ConfigResult]:
    """Test a list of configurations concurrently."""
    proc = ConfigProcessor(cfg)
    try:
        results = await proc.test_configs(configs, history)
        await proc.write_history_batch(db)
        return results
    finally:
        if proc.tester:
            await proc.tester.close()


def filter_results_by_ping(
    results: list[ConfigResult], settings: Settings
) -> list[ConfigResult]:
    """Filter results based on maximum allowed ping."""
    if settings.filtering.max_ping_ms is None:
        return results
    return [
        r
        for r in results
        if r.ping_time is not None
        and r.ping_time * 1000 <= settings.filtering.max_ping_ms
    ]
