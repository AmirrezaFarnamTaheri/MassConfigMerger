#!/usr/bin/env python3
"""Retest and sort an existing VPN subscription output."""

import asyncio
import argparse
import base64
import binascii
import csv
import sys
from pathlib import Path
from typing import List, Tuple, Optional

from tqdm.asyncio import tqdm_asyncio

from .utils import EnhancedConfigProcessor, print_public_source_warning
from .config import Settings, load_config


async def _test_config(
    proc: EnhancedConfigProcessor, cfg: str
) -> Tuple[str, Optional[float]]:
    host, port = proc.extract_host_port(cfg)
    if host and port:
        ping = await proc.test_connection(host, port)
    else:
        ping = None
    return cfg, ping


async def retest_configs(
    configs: List[str], settings: Settings
) -> List[Tuple[str, Optional[float]]]:
    proc = EnhancedConfigProcessor(settings)
    semaphore = asyncio.Semaphore(settings.concurrent_limit)

    async def worker(cfg: str) -> Tuple[str, Optional[float]]:
        async with semaphore:
            return await _test_config(proc, cfg)

    tasks = [asyncio.create_task(worker(c)) for c in configs]
    try:
        return await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="Testing")
    finally:
        await proc.tester.close()


def load_configs(path: Path) -> List[str]:
    """Load raw or base64-encoded configuration strings from ``path``."""
    text = path.read_text(encoding="utf-8").strip()
    if text and "://" not in text.splitlines()[0]:
        try:
            decoded_bytes = base64.b64decode(text)
            text = decoded_bytes.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as e:
            raise ValueError("Failed to decode base64 input") from e
    return [line.strip() for line in text.splitlines() if line.strip()]


def filter_configs(configs: List[str], settings: Settings) -> List[str]:
    """Filter configs based on include/exclude protocol settings."""
    if settings.include_protocols is None and settings.exclude_protocols is None:
        return configs

    proc = EnhancedConfigProcessor(settings)
    filtered = []
    for cfg in configs:
        proto = proc.categorize_protocol(cfg).upper()
        if settings.include_protocols and proto not in settings.include_protocols:
            continue
        if settings.exclude_protocols and proto in settings.exclude_protocols:
            continue
        filtered.append(cfg)
    return filtered


def save_results(
    results: List[Tuple[str, Optional[float]]],
    settings: Settings,
    sort: bool,
    top_n: int,
) -> None:
    output_dir = Path(settings.output_dir)
    output_dir.mkdir(exist_ok=True)

    if sort:
        results.sort(
            key=lambda x: (x[1] is None, x[1] if x[1] is not None else float("inf"))
        )

    if top_n > 0:
        results = results[:top_n]

    configs = [c for c, _ in results]
    raw_path = output_dir / "vpn_retested_raw.txt"
    raw_path.write_text("\n".join(configs), encoding="utf-8")

    if settings.write_base64:
        base64_path = output_dir / "vpn_retested_base64.txt"
        base64_path.write_text(
            base64.b64encode("\n".join(configs).encode()).decode(), encoding="utf-8"
        )

    if settings.write_csv:
        csv_path = output_dir / "vpn_retested_detailed.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Config", "Ping_MS"])
            for cfg, ping in results:
                writer.writerow(
                    [cfg, round(ping * 1000, 2) if ping is not None else ""]
                )

    print(f"\n✔ Retested files saved in {output_dir}/")


async def run_retester(
    cfg: Settings,
    input_file: Path,
    sort: bool,
    top_n: int,
):
    """Asynchronous runner for the retesting functionality."""
    configs = load_configs(input_file)
    configs = filter_configs(configs, cfg)
    results = await retest_configs(configs, cfg)
    if cfg.max_ping_ms is not None:
        results = [
            (c, p)
            for c, p in results
            if p is not None and p * 1000 <= cfg.max_ping_ms
        ]
    save_results(results, cfg, sort, top_n)


# This file is not intended to be run directly anymore.
# The main entry point is now cli.py.