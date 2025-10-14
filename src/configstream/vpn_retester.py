# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Core logic for the VPN retesting pipeline.

This module orchestrates the retesting process by delegating core tasks
to the `processing` module.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import csv
import logging
from pathlib import Path

from .config import Settings
from .constants import (
    RETESTED_BASE64_FILE_NAME,
    RETESTED_CSV_FILE_NAME,
    RETESTED_RAW_FILE_NAME,
)
from .core.config_processor import categorize_protocol
from .db import Database
from .processing import pipeline


def load_configs_from_file(path: Path) -> list[str]:
    """Load raw or base64-encoded configuration strings from a file."""
    text = path.read_text(encoding="utf-8").strip()
    if text and "://" not in text.splitlines()[0]:
        try:
            decoded_bytes = base64.b64decode(text)
            text = decoded_bytes.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as e:
            raise ValueError("Failed to decode base64 input") from e
    return [line.strip() for line in text.splitlines() if line.strip()]


def filter_configs_by_protocol(configs: list[str], settings: Settings) -> list[str]:
    """Filter configurations based on the merge include/exclude protocol settings."""
    if (
        not settings.filtering.merge_include_protocols
        and not settings.filtering.merge_exclude_protocols
    ):
        return configs

    filtered = []
    for cfg in configs:
        proto = categorize_protocol(cfg).upper()
        if (
            settings.filtering.merge_include_protocols
            and proto not in settings.filtering.merge_include_protocols
        ):
            continue
        if (
            settings.filtering.merge_exclude_protocols
            and proto in settings.filtering.merge_exclude_protocols
        ):
            continue
        filtered.append(cfg)
    return filtered


def save_retest_results(
    results: list[pipeline.ConfigResult],
    settings: Settings,
) -> None:
    """Save the retested configurations to output files."""
    output_dir = Path(settings.output.output_dir)
    output_dir.mkdir(exist_ok=True)

    configs = [r.config for r in results]
    raw_path = output_dir / RETESTED_RAW_FILE_NAME
    raw_path.write_text("\n".join(configs), encoding="utf-8")

    if settings.output.write_base64:
        base64_path = output_dir / RETESTED_BASE64_FILE_NAME
        base64_path.write_text(
            base64.b64encode("\n".join(configs).encode()).decode(), encoding="utf-8"
        )

    if settings.output.write_csv:
        csv_path = output_dir / RETESTED_CSV_FILE_NAME
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Config", "Ping_MS", "Protocol", "Country"])
            for r in results:
                writer.writerow(
                    [
                        r.config,
                        round(r.ping_time * 1000, 2) if r.ping_time is not None else "",
                        r.protocol,
                        r.country or "",
                    ]
                )

    print(f"\n✔ Retested files saved in {output_dir}/")


async def run_retester(
    cfg: Settings,
    input_file: Path,
):
    """Asynchronous runner for the retesting functionality."""
    db = Database(cfg.output.history_db_file)
    await db.connect()
    history = await db.get_proxy_history()

    try:
        configs = load_configs_from_file(input_file)
        configs = filter_configs_by_protocol(configs, cfg)
        results = await pipeline.test_configs(configs, cfg, history, db)
        results = pipeline.filter_results_by_ping(results, cfg)
        processed_results = pipeline.sort_and_trim_results(results, cfg)
        save_retest_results(processed_results, cfg)
        return [r.to_dict() for r in processed_results]
    finally:
        await db.close()


def run_retester_flow(settings: Settings) -> list[dict]:
    """Synchronous wrapper for the retesting flow."""
    if (
        not settings.processing.resume_file
        or not settings.processing.resume_file.exists()
    ):
        logging.error("Retesting requires a valid resume_file path.")
        return []

    try:
        # Get the current running event loop or create a new one
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    results = loop.run_until_complete(
        run_retester(settings, settings.processing.resume_file)
    )
    return results
