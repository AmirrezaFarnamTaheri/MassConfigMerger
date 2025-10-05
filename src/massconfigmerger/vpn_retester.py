"""Core logic for the VPN retesting pipeline.

This module provides the `run_retester` function, which orchestrates the
process of loading an existing subscription file, re-testing the connectivity
of each configuration, and writing the updated results to new output files.
It is designed to be used as part of the `retest` command.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import csv
from pathlib import Path
from typing import List

from tqdm.asyncio import tqdm_asyncio

from .config import Settings
from .core import config_normalizer
from .core.config_processor import ConfigProcessor, ConfigResult
from .core.utils import get_sort_key
from .db import Database


async def _test_config(
    proc: ConfigProcessor, cfg: str, history: dict
) -> ConfigResult:
    """
    Test a single configuration and return a ConfigResult object.

    Args:
        proc: The ConfigProcessor instance to use for testing.
        cfg: The configuration string to test.
        history: The proxy history from the database.

    Returns:
        A ConfigResult object containing the test results.
    """
    host, port = config_normalizer.extract_host_port(cfg)
    ping, country = None, None
    if host and port:
        ping, country = await asyncio.gather(
            proc.test_connection(host, port), proc.lookup_country(host)
        )

    key = f"{host}:{port}"
    stats = history.get(key)
    reliability = None
    if stats and (stats["successes"] + stats["failures"]) > 0:
        reliability = stats["successes"] / (stats["successes"] + stats["failures"])

    return ConfigResult(
        config=cfg,
        is_reachable=ping is not None,
        ping_time=ping,
        protocol=proc.categorize_protocol(cfg),
        host=host,
        port=port,
        country=country,
        reliability=reliability,
    )


async def retest_configs(
    configs: List[str], settings: Settings, history: dict
) -> List[ConfigResult]:
    """
    Test a list of configurations concurrently for connectivity and latency.

    Args:
        configs: A list of configuration strings to test.
        settings: The application settings.
        history: The proxy history from the database.

    Returns:
        A list of ConfigResult objects with the test results.
    """
    proc = ConfigProcessor(settings)
    semaphore = asyncio.Semaphore(settings.network.concurrent_limit)

    async def worker(cfg: str) -> ConfigResult:
        async with semaphore:
            return await _test_config(proc, cfg, history)

    tasks = [asyncio.create_task(worker(c)) for c in configs]
    try:
        return await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="Retesting")
    finally:
        if proc.tester:
            await proc.tester.close()


def load_configs_from_file(path: Path) -> List[str]:
    """
    Load raw or base64-encoded configuration strings from a file.

    Args:
        path: The path to the input file.

    Returns:
        A list of configuration strings.

    Raises:
        ValueError: If the file content is not valid raw or base64-encoded text.
    """
    text = path.read_text(encoding="utf-8").strip()
    if text and "://" not in text.splitlines()[0]:
        try:
            decoded_bytes = base64.b64decode(text)
            text = decoded_bytes.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as e:
            raise ValueError("Failed to decode base64 input") from e
    return [line.strip() for line in text.splitlines() if line.strip()]


def filter_configs_by_protocol(configs: List[str], settings: Settings) -> List[str]:
    """
    Filter configurations based on the merge include/exclude protocol settings.

    Args:
        configs: A list of configuration strings to filter.
        settings: The application settings.

    Returns:
        A new list containing only the configurations that match the rules.
    """
    if (
        not settings.filtering.merge_include_protocols
        and not settings.filtering.merge_exclude_protocols
    ):
        return configs

    proc = ConfigProcessor(settings)
    filtered = []
    for cfg in configs:
        proto = proc.categorize_protocol(cfg).upper()
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


def filter_results_by_ping(
    results: List[ConfigResult], settings: Settings
) -> List[ConfigResult]:
    """Filter results based on maximum allowed ping."""
    if settings.filtering.max_ping_ms is None:
        return results
    return [
        r
        for r in results
        if r.ping_time is not None
        and r.ping_time * 1000 <= settings.filtering.max_ping_ms
    ]


def process_results(
    results: List[ConfigResult], settings: Settings
) -> List[ConfigResult]:
    """Sort and apply top-N filtering to the results."""
    if settings.processing.enable_sorting:
        results.sort(key=get_sort_key(settings.processing.sort_by))

    if settings.processing.top_n > 0:
        results = results[: settings.processing.top_n]

    return results


def save_retest_results(
    results: List[ConfigResult],
    settings: Settings,
) -> None:
    """
    Save the retested configurations to output files.

    Args:
        results: A list of ConfigResult objects from the retesting process.
        settings: The application settings.
    """
    output_dir = Path(settings.output.output_dir)
    output_dir.mkdir(exist_ok=True)

    configs = [r.config for r in results]
    raw_path = output_dir / "vpn_retested_raw.txt"
    raw_path.write_text("\n".join(configs), encoding="utf-8")

    if settings.output.write_base64:
        base64_path = output_dir / "vpn_retested_base64.txt"
        base64_path.write_text(
            base64.b64encode("\n".join(configs).encode()).decode(), encoding="utf-8"
        )

    if settings.output.write_csv:
        csv_path = output_dir / "vpn_retested_detailed.csv"
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
    """
    Asynchronous runner for the retesting functionality.

    This function orchestrates the entire retesting process, including loading,
    filtering, testing, and saving the results.

    Args:
        cfg: The application settings.
        input_file: The path to the subscription file to retest.
    """
    db = Database(cfg.output.history_db_file)
    await db.connect()
    history = await db.get_proxy_history()

    try:
        configs = load_configs_from_file(input_file)
        configs = filter_configs_by_protocol(configs, cfg)
        results = await retest_configs(configs, cfg, history)
        results = filter_results_by_ping(results, cfg)
        processed_results = process_results(results, cfg)
        save_retest_results(processed_results, cfg)

        # Update history
        for result in processed_results:
            if result.host and result.port:
                key = f"{result.host}:{result.port}"
                await db.update_proxy_history(key, result.is_reachable)
    finally:
        await db.close()
