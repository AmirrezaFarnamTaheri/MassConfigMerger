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
from typing import List, Optional

from tqdm.asyncio import tqdm_asyncio

from .config import Settings
from .core.config_processor import ConfigProcessor, ConfigResult
from .core.utils import get_sort_key
from .core import config_normalizer


async def _test_config(proc: ConfigProcessor, cfg: str) -> ConfigResult:
    """
    Test a single configuration and return a ConfigResult object.

    Args:
        proc: The ConfigProcessor instance to use for testing.
        cfg: The configuration string to test.

    Returns:
        A ConfigResult object containing the test results.
    """
    host, port = config_normalizer.extract_host_port(cfg)
    ping, country = None, None
    if host and port:
        ping, country = await asyncio.gather(
            proc.test_connection(host, port), proc.lookup_country(host)
        )

    return ConfigResult(
        config=cfg,
        is_reachable=ping is not None,
        ping_time=ping,
        protocol=proc.categorize_protocol(cfg),
        host=host,
        port=port,
        country=country,
    )


async def retest_configs(
    configs: List[str], settings: Settings
) -> List[ConfigResult]:
    """
    Test a list of configurations concurrently for connectivity and latency.

    Args:
        configs: A list of configuration strings to test.
        settings: The application settings.

    Returns:
        A list of ConfigResult objects with the test results.
    """
    proc = ConfigProcessor(settings)
    semaphore = asyncio.Semaphore(settings.network.concurrent_limit)

    async def worker(cfg: str) -> ConfigResult:
        async with semaphore:
            return await _test_config(proc, cfg)

    tasks = [asyncio.create_task(worker(c)) for c in configs]
    try:
        return await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="Retesting")
    finally:
        if proc.tester:
            await proc.tester.close()


def load_configs(path: Path) -> List[str]:
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


def filter_configs(configs: List[str], settings: Settings) -> List[str]:
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


def save_results(
    results: List[ConfigResult],
    settings: Settings,
) -> None:
    """
    Sort, filter, and save the retested configurations to output files.

    Args:
        results: A list of ConfigResult objects from the retesting process.
        settings: The application settings.
    """
    output_dir = Path(settings.output.output_dir)
    output_dir.mkdir(exist_ok=True)

    if settings.processing.enable_sorting:
        results.sort(key=get_sort_key(settings.processing.sort_by))

    if settings.processing.top_n > 0:
        results = results[: settings.processing.top_n]

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
    configs = load_configs(input_file)
    configs = filter_configs(configs, cfg)
    results = await retest_configs(configs, cfg)
    if cfg.filtering.max_ping_ms is not None:
        results = [
            r
            for r in results
            if r.ping_time is not None
            and r.ping_time * 1000 <= cfg.filtering.max_ping_ms
        ]
    save_results(results, cfg)