"""Handles writing all output files.

This module is responsible for generating and writing all the different
output formats, such as raw config lists, base64-encoded subscriptions,
Clash proxies, and various reports. It acts as an orchestrator, calling
more specialized generators as needed.
"""
from __future__ import annotations

import base64
import csv
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .core.proxy_parser import ProxyParser
from .constants import (
    BASE64_SUBSCRIPTION_FILE_NAME,
    CLASH_PROXIES_FILE_NAME,
    CSV_REPORT_FILE_NAME,
    RAW_SUBSCRIPTION_FILE_NAME,
)
from .core.config_processor import ConfigResult


def write_raw_configs(configs: List[str], output_dir: Path, prefix: str = "") -> Path:
    """Write raw config links to a file."""
    raw_file = output_dir / f"{prefix}{RAW_SUBSCRIPTION_FILE_NAME}"
    tmp_file = raw_file.with_suffix(raw_file.suffix + ".tmp")
    tmp_file.write_text("\n".join(configs), encoding="utf-8")
    tmp_file.replace(raw_file)
    return raw_file


def write_base64_configs(configs: List[str], output_dir: Path, prefix: str = "") -> Path:
    """Write base64-encoded config links to a file."""
    base64_file = output_dir / f"{prefix}{BASE64_SUBSCRIPTION_FILE_NAME}"
    base64_content = base64.b64encode(
        "\n".join(configs).encode("utf-8")).decode("utf-8")
    base64_file.write_text(base64_content, encoding="utf-8")
    return base64_file


def write_csv_report(results: List[ConfigResult], output_dir: Path, prefix: str = "") -> Path:
    """Write a detailed CSV report of the results."""
    csv_file = output_dir / f"{prefix}{CSV_REPORT_FILE_NAME}"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "config",
                "protocol",
                "host",
                "port",
                "ping_ms",
                "reachable",
                "source_url",
                "country",
            ]
        )
        for result in results:
            ping_ms = round(result.ping_time * 1000,
                            2) if result.ping_time else None
            writer.writerow(
                [
                    result.config,
                    result.protocol,
                    result.host,
                    result.port,
                    ping_ms,
                    result.is_reachable,
                    result.source_url,
                    result.country,
                ]
            )
    return csv_file


def write_clash_proxies(
    results: List[ConfigResult], output_dir: Path, prefix: str = ""
) -> Path:
    """Generate and write a Clash proxies-only file."""
    parser = ProxyParser()
    proxies: List[Dict[str, Any]] = []
    for idx, r in enumerate(results):
        proxy = parser.config_to_clash_proxy(r.config, idx, r.protocol)
        if proxy:
            proxies.append(proxy)

    proxy_yaml = yaml.safe_dump(
        {"proxies": proxies}, allow_unicode=True, sort_keys=False
    )
    proxies_file = output_dir / f"{prefix}{CLASH_PROXIES_FILE_NAME}"
    proxies_file.write_text(proxy_yaml, encoding="utf-8")
    return proxies_file