"""Main processing pipeline"""

import aiohttp
import json
import base64
from pathlib import Path
from typing import List, Optional
from rich.progress import Progress
import geoip2.database

from .core import Proxy, parse_config, geolocate_proxy
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

import asyncio
from typing import List, AsyncIterator
from .config import ProxyConfig
from .security.malicious_detector import MaliciousNodeDetector
from .security.rate_limiter import RateLimiter

async def process_proxies_in_batches(proxies: List[Proxy],
                                    processor_func,
                                    batch_size: Optional[int] = None) -> AsyncIterator[List[Proxy]]:
    """
    Process proxies in batches to manage memory efficiently.

    This prevents loading all proxies into memory at once, which is critical
    for large proxy lists that could cause out-of-memory errors.

    Args:
        proxies: List of proxy objects to process
        processor_func: Async function that processes a batch
        batch_size: Size of each batch (default from config)

    Yields:
        Processed batches of proxies
    """
    config = ProxyConfig()
    batch_size = batch_size or config.BATCH_SIZE

    for i in range(0, len(proxies), batch_size):
        batch = proxies[i:i + batch_size]
        processed_batch = await processor_func(batch)
        yield processed_batch

        # Allow garbage collection between batches
        await asyncio.sleep(0.1)


async def test_proxies_batched(proxies: List[Proxy],
                              tester,
                              malicious_detector) -> List[Proxy]:
    """
    Test proxies with memory-efficient batch processing.
    """
    config = ProxyConfig()
    tested_proxies = []

    async def process_batch(batch: List[Proxy]) -> List[Proxy]:
        results = []
        for proxy in batch:
            # Test connectivity
            tested_proxy = await tester.test(proxy)

            # Skip malicious detection for failed proxies
            if tested_proxy.is_working:
                # Run security tests
                security_results = await malicious_detector.detect_malicious(tested_proxy)

                if security_results['is_malicious']:
                    tested_proxy.is_working = False
                    tested_proxy.security_issues.append(
                        f"Malicious: {security_results['severity']} - "
                        f"{len([t for t in security_results['tests'] if not t.passed])} tests failed"
                    )

            results.append(tested_proxy)

        return results

    async for batch_results in process_proxies_in_batches(
        proxies, process_batch, config.BATCH_SIZE
    ):
        tested_proxies.extend(batch_results)

    return tested_proxies

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
    config = ProxyConfig()
    detector = MaliciousNodeDetector()
    rate_limiter = RateLimiter(
        requests_per_second=config.RATE_LIMIT_REQUESTS / config.RATE_LIMIT_WINDOW
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    task = progress.add_task("[cyan]Processing proxies...", total=100)

    if not proxies:
        # Fetch configurations
        all_configs = []
        async with aiohttp.ClientSession() as session:
            for source in sources:
                if rate_limiter.is_allowed(source):
                    configs = await fetch_configs(session, source)
                    all_configs.extend(configs)
                else:
                    # Handle rate limited source if necessary
                    pass

        progress.update(task, completed=20)

        # Parse and geolocate configurations
        proxies = []
        geoip_reader = None
        try:
            geoip_db_path = Path("data/GeoLite2-City.mmdb")
            if geoip_db_path.exists():
                geoip_reader = geoip2.database.Reader(str(geoip_db_path))
        except Exception as e:
            print(f"Could not load GeoIP database: {e}")

        for config_str in all_configs[:max_proxies] if max_proxies else all_configs:
            proxy = parse_config(config_str)
            if proxy:
                proxy = geolocate_proxy(proxy, geoip_reader)
                proxies.append(proxy)

        if geoip_reader:
            geoip_reader.close()

    progress.update(task, completed=40)

    # Test proxies
    tested_proxies = await test_proxies_batched(
        proxies,
        tester=SingBoxTester(),
        malicious_detector=detector
    )

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
        "cache_bust": int(datetime.now().timestamp() * 1000),
        "protocol_colors": config.PROTOCOL_COLORS
    }
    output_path.joinpath("metadata.json").write_text(json.dumps(metadata, indent=2))

    progress.update(task, completed=100)
