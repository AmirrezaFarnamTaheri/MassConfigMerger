from __future__ import annotations

import base64
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import yaml

from .clash_utils import config_to_clash_proxy
from .result_processor import CONFIG, ConfigResult

EXCLUDE_REGEXES: List[re.Pattern] = []


def build_html_report(results: List[ConfigResult]) -> str:
    """Return a simple HTML table summarizing results."""
    rows = []
    for r in results:
        latency = round(r.ping_time * 1000, 2) if r.ping_time else ""
        country = r.country or ""
        host = r.host or ""
        rows.append(
            f"<tr><td>{r.protocol}</td><td>{host}</td><td>{latency}</td><td>{country}</td></tr>"
        )
    header = (
        "<html><head><meta charset='utf-8'><title>VPN Report</title></head><body>"
        "<table border='1'>"
        "<tr><th>Protocol</th><th>Host</th><th>Latency (ms)</th><th>Country</th></tr>"
    )
    footer = "</table></body></html>"
    return header + "".join(rows) + footer

async def generate_comprehensive_outputs(
    merger: Any,
    results: List[ConfigResult],
    stats: Dict,
    start_time: float,
    prefix: str = "",
) -> None:
    """Generate comprehensive output files with all formats."""
    async with merger._file_lock, merger.seen_hashes_lock:
        output_dir = Path(CONFIG.output_dir)
        output_dir.mkdir(exist_ok=True)

        configs = [result.config for result in results]

        raw_file = output_dir / f"{prefix}vpn_subscription_raw.txt"
        tmp_raw = raw_file.with_suffix('.tmp')
        tmp_raw.write_text("\n".join(configs), encoding="utf-8")
        tmp_raw.replace(raw_file)

        base64_file = output_dir / f"{prefix}vpn_subscription_base64.txt"
        if CONFIG.write_base64:
            base64_content = base64.b64encode("\n".join(configs).encode("utf-8")).decode("utf-8")
            tmp_base64 = base64_file.with_suffix('.tmp')
            tmp_base64.write_text(base64_content, encoding="utf-8")
            tmp_base64.replace(base64_file)

        csv_file = output_dir / f"{prefix}vpn_detailed.csv"
        if CONFIG.write_csv:
            tmp_csv = csv_file.with_suffix('.tmp')
            with open(tmp_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'config', 'protocol', 'host', 'port',
                    'ping_ms', 'reachable', 'source_url', 'country'
                ])
                for result in results:
                    ping_ms = round(result.ping_time * 1000, 2) if result.ping_time else None
                    writer.writerow([
                        result.config,
                        result.protocol,
                        result.host,
                        result.port,
                        ping_ms,
                        result.is_reachable,
                        result.source_url,
                        result.country,
                    ])
            tmp_csv.replace(csv_file)

        if CONFIG.write_html:
            html_file = output_dir / f"{prefix}vpn_report.html"
            tmp_html = html_file.with_suffix('.tmp')
            tmp_html.write_text(build_html_report(results), encoding="utf-8")
            tmp_html.replace(html_file)

        report_file = output_dir / f"{prefix}vpn_report.json"
        report = {
            "generation_info": {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "processing_time_seconds": round(time.time() - start_time, 2),
                "script_version": "Unified & Polished Edition",
                "url_testing_enabled": CONFIG.enable_url_testing,
                "sorting_enabled": CONFIG.enable_sorting,
            },
            "statistics": stats,
            "source_categories": {
                "total_unique_sources": len(merger.sources)
            },
            "output_files": {
                "raw": str(raw_file),
                **({"base64": str(base64_file)} if CONFIG.write_base64 else {}),
                **({"detailed_csv": str(csv_file)} if CONFIG.write_csv else {}),
                "json_report": str(report_file),
                **({"html_report": str(output_dir / f"{prefix}vpn_report.html")} if CONFIG.write_html else {}),
                "singbox": str(output_dir / f"{prefix}vpn_singbox.json"),
                "clash": str(output_dir / f"{prefix}clash.yaml"),
                **(
                    {"clash_proxies": str(output_dir / f"{prefix}vpn_clash_proxies.yaml")}
                    if CONFIG.write_clash_proxies
                    else {}
                ),
            },
            "usage_instructions": {
                "base64_subscription": "Copy content of base64 file as subscription URL",
                "raw_subscription": "Host raw file and use URL as subscription link",
                "csv_analysis": "Use CSV file for detailed analysis and custom filtering",
                "clash_yaml": "Load clash.yaml in Clash Meta or Stash",
                "clash_proxies_yaml": "Import vpn_clash_proxies.yaml as a simple provider",
                "supported_clients": [
                    "V2rayNG", "V2rayN", "Hiddify Next", "Shadowrocket",
                    "NekoBox", "Clash Meta", "Sing-Box", "Streisand", "Karing"
                ]
            }
        }

        tmp_report = report_file.with_suffix('.tmp')
        tmp_report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_report.replace(report_file)

        outbounds = []
        for idx, r in enumerate(results):
            tag = re.sub(r"[^A-Za-z0-9_-]+", "-", f"{r.protocol}-{idx}")
            ob = {
                "type": r.protocol.lower(),
                "tag": tag,
                "server": r.host or "",
                "server_port": r.port,
                "raw": r.config
            }
            ob.update(merger._parse_extra_params(r.config))
            if r.country:
                ob["country"] = r.country
            outbounds.append(ob)

        singbox_file = output_dir / f"{prefix}vpn_singbox.json"
        tmp_singbox = singbox_file.with_suffix('.tmp')
        tmp_singbox.write_text(json.dumps({"outbounds": outbounds}, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_singbox.replace(singbox_file)

        if CONFIG.write_clash:
            clash_yaml = merger._results_to_clash_yaml(results)
            clash_file = output_dir / f"{prefix}clash.yaml"
            tmp_clash = clash_file.with_suffix('.tmp')
            tmp_clash.write_text(clash_yaml, encoding="utf-8")
            tmp_clash.replace(clash_file)

        need_proxies = (
            CONFIG.write_clash_proxies
            or CONFIG.surge_file
            or CONFIG.qx_file
            or CONFIG.xyz_file
        )
        proxies: List[Dict[str, Any]] = []
        if need_proxies:
            for idx, r in enumerate(results):
                proxy = config_to_clash_proxy(r.config, idx, r.protocol)
                if proxy:
                    proxies.append(proxy)

        if CONFIG.write_clash_proxies:
            proxy_yaml = yaml.safe_dump({"proxies": proxies}, allow_unicode=True, sort_keys=False) if proxies else ""
            proxies_file = output_dir / f"{prefix}vpn_clash_proxies.yaml"
            tmp_proxies = proxies_file.with_suffix('.tmp')
            tmp_proxies.write_text(proxy_yaml, encoding="utf-8")
            tmp_proxies.replace(proxies_file)

        if CONFIG.surge_file:
            from .advanced_converters import generate_surge_conf
            surge_content = generate_surge_conf(proxies)
            surge_file = Path(CONFIG.surge_file)
            if not surge_file.is_absolute():
                surge_file = output_dir / surge_file
            tmp_surge = surge_file.with_suffix('.tmp')
            tmp_surge.write_text(surge_content, encoding="utf-8")
            tmp_surge.replace(surge_file)

        if CONFIG.qx_file:
            from .advanced_converters import generate_qx_conf
            qx_content = generate_qx_conf(proxies)
            qx_file = Path(CONFIG.qx_file)
            if not qx_file.is_absolute():
                qx_file = output_dir / qx_file
            tmp_qx = qx_file.with_suffix('.tmp')
            tmp_qx.write_text(qx_content, encoding="utf-8")
            tmp_qx.replace(qx_file)

        if CONFIG.xyz_file:
            xyz_lines = [
                f"{p.get('name')},{p.get('server')},{p.get('port')}" for p in proxies
            ]
            xyz_file = Path(CONFIG.xyz_file)
            if not xyz_file.is_absolute():
                xyz_file = output_dir / xyz_file
            tmp_xyz = xyz_file.with_suffix('.tmp')
            tmp_xyz.write_text("\n".join(xyz_lines), encoding="utf-8")
            tmp_xyz.replace(xyz_file)

async def upload_files_to_gist(paths: List[Path], token: str, *, base_url: str = "https://api.github.com") -> Dict[str, str]:
    """Upload files as separate private gists and return name->raw_url mapping."""
    import aiohttp

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    result: Dict[str, str] = {}
    base = base_url.rstrip("/") + "/gists"
    async with aiohttp.ClientSession(headers=headers) as session:
        for path in paths:
            payload = {
                "files": {path.name: {"content": path.read_text(encoding="utf-8")}},
                "public": False,
                "description": "MassConfigMerger output",
            }
            async with session.post(base, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                raw = data["files"][path.name]["raw_url"]
                result[path.name] = raw
    return result


def write_upload_links(links: Dict[str, str], output_dir: Path) -> Path:
    """Write uploaded file links to output_dir/upload_links.txt and return the path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / "upload_links.txt"
    tmp = dest.with_suffix(".tmp")
    tmp.write_text("\n".join(f"{k}: {v}" for k, v in links.items()), encoding="utf-8")
    tmp.replace(dest)
    return dest
