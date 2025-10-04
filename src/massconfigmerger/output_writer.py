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

from .advanced_converters import generate_qx_conf, generate_surge_conf
from .clash_utils import config_to_clash_proxy
from .config import Settings
from .core.config_processor import ConfigResult
from .report_generator import generate_html_report, generate_json_report


def write_raw_configs(configs: List[str], output_dir: Path, prefix: str = "") -> Path:
    """Write raw config links to a file."""
    raw_file = output_dir / f"{prefix}vpn_subscription_raw.txt"
    raw_file.write_text("\n".join(configs), encoding="utf-8")
    return raw_file

def write_base64_configs(configs: List[str], output_dir: Path, prefix: str = "") -> Path:
    """Write base64-encoded config links to a file."""
    base64_file = output_dir / f"{prefix}vpn_subscription_base64.txt"
    base64_content = base64.b64encode("\n".join(configs).encode("utf-8")).decode("utf-8")
    base64_file.write_text(base64_content, encoding="utf-8")
    return base64_file

def write_csv_report(results: List[ConfigResult], output_dir: Path, prefix: str = "") -> Path:
    """Write a detailed CSV report of the results."""
    csv_file = output_dir / f"{prefix}vpn_detailed.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(
            ['config', 'protocol', 'host', 'port', 'ping_ms', 'reachable', 'source_url', 'country']
        )
        for result in results:
            ping_ms = round(result.ping_time * 1000, 2) if result.ping_time else None
            writer.writerow([
                result.config, result.protocol, result.host, result.port,
                ping_ms, result.is_reachable, result.source_url, result.country,
            ])
    return csv_file

def write_clash_proxies(results: List[ConfigResult], output_dir: Path, prefix: str = "") -> Path:
    """Generate and write a Clash proxies-only file."""
    proxies: List[Dict[str, Any]] = []
    for idx, r in enumerate(results):
        proxy = config_to_clash_proxy(r.config, idx, r.protocol)
        if proxy:
            proxies.append(proxy)

    proxy_yaml = yaml.safe_dump({"proxies": proxies}, allow_unicode=True, sort_keys=False)
    proxies_file = output_dir / f"{prefix}vpn_clash_proxies.yaml"
    proxies_file.write_text(proxy_yaml, encoding="utf-8")
    return proxies_file

def write_all_outputs(
    results: List[ConfigResult],
    settings: Settings,
    stats: Dict[str, Any],
    start_time: float,
    prefix: str = "",
) -> List[Path]:
    """Orchestrate writing all configured output files."""
    output_dir = Path(settings.output.output_dir)
    output_dir.mkdir(exist_ok=True)

    written_files: List[Path] = []
    configs = [r.config for r in results]

    written_files.append(write_raw_configs(configs, output_dir, prefix))
    if settings.output.write_base64:
        written_files.append(write_base64_configs(configs, output_dir, prefix))
    if settings.output.write_csv:
        written_files.append(write_csv_report(results, output_dir, prefix))
    if settings.output.write_html:
        written_files.append(generate_html_report(results, output_dir, prefix))
    if settings.output.write_clash_proxies:
        written_files.append(write_clash_proxies(results, output_dir, prefix))

    # Generate JSON report
    written_files.append(
        generate_json_report(results, stats, output_dir, start_time, settings, prefix)
    )

    # Generate advanced formats if configured
    proxies: List[Dict[str, Any]] = []
    if settings.output.surge_file or settings.output.qx_file:
        for idx, r in enumerate(results):
            proxy = config_to_clash_proxy(r.config, idx, r.protocol)
            if proxy:
                proxies.append(proxy)

    if settings.output.surge_file:
        surge_content = generate_surge_conf(proxies)
        surge_file = output_dir / settings.output.surge_file
        surge_file.write_text(surge_content, encoding="utf-8")
        written_files.append(surge_file)

    if settings.output.qx_file:
        qx_content = generate_qx_conf(proxies)
        qx_file = output_dir / settings.output.qx_file
        qx_file.write_text(qx_content, encoding="utf-8")
        written_files.append(qx_file)

    return written_files