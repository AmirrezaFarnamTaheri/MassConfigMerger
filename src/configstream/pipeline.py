import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import aiohttp
import geoip2.database
from rich.progress import Progress

from .core import Proxy, ProxyTester, geolocate_proxy
from .core import parse_config_batch
from .output import (generate_base64_subscription, generate_clash_config,
                     generate_singbox_config)

logger = logging.getLogger(__name__)


async def run_full_pipeline(
    sources: List[str],
    output_dir: str,
    progress: Optional[Progress] = None,
    max_workers: int = 10,
    max_proxies: Optional[int] = None,
    country_filter: Optional[str] = None,
    min_latency: Optional[int] = None,
    max_latency: Optional[int] = None,
    timeout: int = 10,
    proxies: Optional[List[Proxy]] = None,
) -> dict:
    start_time = datetime.now(timezone.utc)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    stats = {
        "fetched": 0,
        "tested": 0,
        "working": 0,
        "filtered": 0,
    }

    try:
        logger.info(f"Starting pipeline with {len(sources)} sources")

        if progress:
            fetch_task = progress.add_task("Fetching configs...",
                                           total=len(sources))

        all_configs = []

        async with aiohttp.ClientSession() as session:
            tasks = [_fetch_source(session, source) for source in sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for source, result in zip(sources, results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch {source}: {result}")
                    continue

                configs, count = result
                all_configs.extend(configs)
                stats["fetched"] += count

                if progress:
                    progress.update(fetch_task, advance=1)

        logger.info(f"Fetched {stats['fetched']} proxy configurations")

        if stats["fetched"] == 0:
            logger.error("No configurations fetched from any source")
            return {
                "success": False,
                "stats": stats,
                "output_files": {},
                "error": "No configurations fetched",
            }

        if progress:
            parse_task = progress.add_task("Parsing configs...",
                                           total=stats["fetched"])

        proxies = parse_config_batch(all_configs)

        logger.info(f"Successfully parsed {len(proxies)} configurations")

        if progress:
            progress.update(parse_task, completed=stats["fetched"])

        if not proxies:
            logger.error("No configurations could be parsed")
            return {
                "success": False,
                "stats": stats,
                "output_files": {},
                "error": "No configurations could be parsed",
            }

        if max_proxies and len(proxies) > max_proxies:
            logger.info(
                f"Limiting to {max_proxies} proxies (down from {len(proxies)})")
            proxies = proxies[:max_proxies]

        if proxies:
            stats["tested"] = len(proxies)
        else:
            stats["tested"] = 0

        if progress:
            test_task = progress.add_task("Testing proxies...",
                                          total=len(proxies))

        tester = ProxyTester(
            max_workers=max_workers,
            timeout=timeout,
        )

        tested_proxies = []

        for proxy in await tester.test_all(proxies):
            tested_proxies.append(proxy.proxy)
            stats["working"] += 1 if proxy.success else 0

            if progress:
                progress.update(test_task, advance=1)

        logger.info(
            f"Tested {len(tested_proxies)} proxies, {stats['working']} working"
        )

        if progress:
            geo_task = progress.add_task("Geolocating...",
                                         total=len(tested_proxies))

        geoip_reader = None
        try:
            geoip_db_path = Path("data/GeoLite2-City.mmdb")
            if geoip_db_path.exists():
                geoip_reader = geoip2.database.Reader(str(geoip_db_path))
                logger.info("Loaded GeoIP database")
            else:
                logger.warning(f"GeoIP database not found at {geoip_db_path}")
        except Exception as e:
            logger.warning(f"Could not load GeoIP database: {e}")

        for proxy in tested_proxies:
            if proxy.is_working:
                await geolocate_proxy(proxy, geoip_reader)

            if progress:
                progress.update(geo_task, advance=1)

        if geoip_reader:
            geoip_reader.close()

        if progress:
            filter_task = progress.add_task("Filtering...",
                                            total=len(tested_proxies))

        working_proxies = [p for p in tested_proxies if p.is_working]

        if country_filter:
            working_proxies = [
                p for p in working_proxies if p.country_code
                and p.country_code.upper() == country_filter.upper()
            ]
            logger.info(
                f"Filtered to {len(working_proxies)} proxies in {country_filter}"
            )

        if min_latency is not None:
            working_proxies = [
                p for p in working_proxies
                if p.latency and p.latency >= min_latency
            ]
            logger.info(
                f"Filtered to {len(working_proxies)} proxies with latency >= {min_latency}ms"
            )

        if max_latency is not None:
            working_proxies = [
                p for p in working_proxies
                if p.latency and p.latency <= max_latency
            ]
            logger.info(
                f"Filtered to {len(working_proxies)} proxies with latency <= {max_latency}ms"
            )

        working_proxies.sort(key=lambda p: p.latency or float('inf'))

        stats["filtered"] = len(working_proxies)

        if progress:
            progress.update(filter_task, completed=len(tested_proxies))

        logger.info(
            f"Final result: {stats['filtered']} proxies after filtering")

        if not working_proxies:
            logger.warning("No proxies passed all filters")

        if progress:
            gen_task = progress.add_task("Generating outputs...", total=4)

        output_files = {}

        try:
            sub_content = generate_base64_subscription(working_proxies)
            sub_path = output_path / "vpn_subscription_base64.txt"
            sub_path.write_text(sub_content)
            output_files["subscription"] = str(sub_path)
            if progress:
                progress.update(gen_task, advance=1)

            clash_content = generate_clash_config(working_proxies)
            clash_path = output_path / "clash.yaml"
            clash_path.write_text(clash_content)
            output_files["clash"] = str(clash_path)
            if progress:
                progress.update(gen_task, advance=1)

            try:
                singbox_content = generate_singbox_config(working_proxies)
                singbox_path = output_path / "singbox.json"
                singbox_path.write_text(singbox_content)
                output_files["singbox"] = str(singbox_path)
            except Exception as e:
                logger.warning(f"Could not generate SingBox format: {e}")
            if progress:
                progress.update(gen_task, advance=1)

            raw_content = "\n".join(p.config for p in working_proxies)
            raw_path = output_path / "configs_raw.txt"
            raw_path.write_text(raw_content)
            output_files["raw"] = str(raw_path)

            proxies_json = []
            for p in working_proxies:
                proxies_json.append({
                    "config": p.config,
                    "protocol": p.protocol,
                    "address": p.address,
                    "port": p.port,
                    "latency_ms": p.latency,
                    "country": p.country,
                    "country_code": p.country_code,
                    "city": p.city,
                    "remarks": p.remarks,
                })

            json_path = output_path / "proxies.json"
            json_path.write_text(json.dumps(proxies_json, indent=2))
            output_files["json"] = str(json_path)
            if progress:
                progress.update(gen_task, advance=1)

            success_rate = (stats["working"] / stats["tested"] *
                            100) if stats["tested"] > 0 else 0
            protocol_counts = {}
            for p in working_proxies:
                protocol_counts[p.protocol] = protocol_counts.get(
                    p.protocol, 0) + 1

            stats_json = {
                "generated_at":
                start_time.isoformat(),
                "generated_now":
                datetime.now(timezone.utc).isoformat(),
                "total_fetched":
                stats["fetched"],
                "total_tested":
                stats["tested"],
                "total_working":
                stats["working"],
                "total_filtered":
                stats["filtered"],
                "success_rate":
                round(success_rate, 2),
                "average_latency_ms":
                round(
                    sum(p.latency for p in working_proxies if p.latency) /
                    len([p for p in working_proxies if p.latency]),
                    2) if working_proxies else 0,
                "protocol_distribution":
                protocol_counts,
                "cache_bust":
                int(datetime.now().timestamp() * 1000),
            }

            stats_path = output_path / "statistics.json"
            stats_path.write_text(json.dumps(stats_json, indent=2))
            output_files["statistics"] = str(stats_path)

            metadata = {
                "version": "1.0.0",
                "generated_at": start_time.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "proxy_count": len(working_proxies),
                "working_count": stats["working"],
                "source_count": len(sources),
                "cache_bust": int(datetime.now().timestamp() * 1000),
                "stats": stats_json,
            }

            metadata_path = output_path / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))
            output_files["metadata"] = str(metadata_path)

        except Exception as e:
            logger.error(f"Failed to generate outputs: {e}")
            return {
                "success": False,
                "stats": stats,
                "output_files": output_files,
                "error": f"Generation failed: {e}",
            }

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"Pipeline completed successfully in {elapsed:.1f} seconds")

        return {
            "success": True,
            "stats": stats,
            "output_files": output_files,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Pipeline failed with exception: {e}", exc_info=True)
        return {
            "success": False,
            "stats": stats,
            "output_files": {},
            "error": f"Pipeline failed: {e}",
        }


async def _fetch_source(session: aiohttp.ClientSession,
                        source_url: str) -> tuple:
    try:
        timeout = aiohttp.ClientTimeout(total=30)

        async with session.get(source_url, timeout=timeout, ssl=True) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")

            text = await response.text()

            if text.strip().count('\n') > 0 and len(text) > 100:
                try:
                    decoded = base64.b64decode(text).decode('utf-8')
                    text = decoded
                except Exception:
                    pass

            configs = [
                line.strip() for line in text.split('\n')
                if line.strip() and not line.strip().startswith('#')
            ]

            logger.debug(f"Fetched {len(configs)} configs from {source_url}")
            return (configs, len(configs))

    except Exception as e:
        logger.error(f"Error fetching {source_url}: {e}")
        raise