"""Generates detailed reports from configuration test results.

This module provides functions to create JSON and HTML reports summarizing
the outcome of a merger or retesting run.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .config import Settings
from .core.config_processor import ConfigResult


def generate_json_report(
    results: List[ConfigResult],
    stats: Dict[str, Any],
    output_dir: Path,
    start_time: float,
    settings: Settings,
    prefix: str = "",
) -> Path:
    """Generate a detailed JSON report."""
    report_file = output_dir / f"{prefix}vpn_report.json"
    report = {
        "generation_info": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "processing_time_seconds": round(time.time() - start_time, 2),
            "url_testing_enabled": settings.processing.enable_url_testing,
            "sorting_enabled": settings.processing.enable_sorting,
        },
        "statistics": stats,
        "results": [
            {
                "config": r.config,
                "protocol": r.protocol,
                "host": r.host,
                "port": r.port,
                "ping_ms": round(r.ping_time * 1000, 2) if r.ping_time else None,
                "country": r.country,
                "is_reachable": r.is_reachable,
                "source_url": r.source_url,
            }
            for r in results
        ],
    }
    tmp_report = report_file.with_suffix(".tmp")
    tmp_report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    tmp_report.replace(report_file)
    return report_file


import html


def generate_html_report(
    results: List[ConfigResult], output_dir: Path, prefix: str = ""
) -> Path:
    """Generate a simple HTML report of the results."""
    rows = []
    for r in results:
        latency = round(r.ping_time * 1000, 2) if r.ping_time else ""
        country = html.escape(r.country or "")
        host = html.escape(r.host or "")
        protocol = html.escape(r.protocol or "")
        rows.append(
            f"<tr><td>{protocol}</td><td>{host}</td><td>{latency}</td><td>{country}</td></tr>"
        )
    header = (
        "<html><head><meta charset='utf-8'><title>VPN Report</title></head><body>"
        "<table border='1'>"
        "<tr><th>Protocol</th><th>Host</th><th>Latency (ms)</th><th>Country</th></tr>"
    )
    footer = "</table></body></html>"
    html_content = header + "".join(rows) + footer

    html_file = output_dir / f"{prefix}vpn_report.html"
    tmp_html = html_file.with_suffix(".tmp")
    tmp_html.write_text(html_content, encoding="utf-8")
    tmp_html.replace(html_file)
    return html_file