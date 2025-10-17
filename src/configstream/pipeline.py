"""Main processing pipeline"""

import asyncio
import aiohttp
import json
import base64
from pathlib import Path
from typing import List, Optional
from rich.progress import Progress

from .core import Proxy, parse_config
from .testers import SingBoxTester
from .core import generate_base64_subscription, generate_clash_config
from datetime import datetime, timezone

async def fetch_configs(session: aiohttp.ClientSession, url: str) -> List[str]:
    """Fetch configurations from a URL"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            text = await response.text()
            content = text.strip()
            # If it's a single long line and decodes to text with scheme prefixes, treat as base64 subscription
            if "\n" not in content:
                try:
                    decoded = base64.b64decode(content + "==", validate=False).decode("utf-8", errors="ignore")
                    # Heuristic: check if decoded contains known scheme prefixes
                    if any(s in decoded for s in ("vmess://", "vless://", "ss://", "trojan://")):
                        return [line.strip() for line in decoded.splitlines() if line.strip()]
                except Exception:
                    pass
            return [line.strip() for line in content.splitlines() if line.strip()]
    except Exception:
        return []

async def run_full_pipeline(
    sources: List[str],
    output_dir: str,
    progress: Progress,
    max_proxies: Optional[int] = None,
    country: Optional[str] = None,
    min_latency: Optional[int] = None,
    max_latency: Optional[int] = None,
    proxies: Optional[List[Proxy]] = None,
):
    """Execute the complete pipeline"""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    task = progress.add_task("[cyan]Processing proxies...", total=100)

    if not proxies:
        # Fetch configurations
        all_configs = []
        async with aiohttp.ClientSession() as session:
            for source in sources:
                configs = await fetch_configs(session, source)
                all_configs.extend(configs)

        progress.update(task, completed=20)

        # Parse configurations
        proxies = []
        for config in all_configs[:max_proxies] if max_proxies else all_configs:
            proxy = parse_config(config)
            if proxy:
                proxies.append(proxy)

    progress.update(task, completed=40)

    # Test proxies
    tester = SingBoxTester()
    tested_proxies = []
    for proxy in proxies:
        tested = await tester.test(proxy)
        tested_proxies.append(tested)

    progress.update(task, completed=60)

    # Filter working proxies
    working_proxies = [p for p in tested_proxies if p.is_working]

    # Apply filters
    if country:
        working_proxies = [p for p in working_proxies if p.country_code == country]
    if min_latency:
        working_proxies = [p for p in working_proxies if p.latency and p.latency >= min_latency]
    if max_latency:
        working_proxies = [p for p in working_proxies if p.latency and p.latency <= max_latency]

    progress.update(task, completed=80)

    # Generate outputs
    output_path.joinpath("vpn_subscription_base64.txt").write_text(
        generate_base64_subscription(working_proxies)
    )
    output_path.joinpath("clash.yaml").write_text(
        generate_clash_config(working_proxies)
    )
    output_path.joinpath("configs_raw.txt").write_text(
        "\n".join([p.config for p in working_proxies])
    )

    # Generate JSON outputs
    proxies_data = [
        {
            "config": p.config,
            "protocol": p.protocol,
            "address": p.address,
            "port": p.port,
            "latency": p.latency,
            "country_code": p.country_code,
            "remarks": p.remarks
        }
        for p in working_proxies
    ]
    output_path.joinpath("proxies.json").write_text(json.dumps(proxies_data, indent=2))

    # Generate statistics
    stats = {
        "total_tested": len(tested_proxies),
        "working": len(working_proxies),
        "failed": len(tested_proxies) - len(working_proxies),
        "success_rate": round(len(working_proxies) / len(tested_proxies) * 100, 2) if tested_proxies else 0
    }
    output_path.joinpath("statistics.json").write_text(json.dumps(stats, indent=2))

    # Generate metadata
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "source_count": len(sources),
        "proxy_count": len(working_proxies),
        "cache_bust": int(datetime.now().timestamp() * 1000)
    }
    output_path.joinpath("metadata.json").write_text(json.dumps(metadata, indent=2))

    progress.update(task, completed=100)
