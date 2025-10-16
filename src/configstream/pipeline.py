from __future__ import annotations

import asyncio
from pathlib import Path
import json

import aiohttp
from rich.progress import Progress

from .core import (
    Proxy,
    generate_base64_subscription,
    generate_clash_config,
    generate_raw_configs,
    generate_proxies_json,
    generate_statistics_json,
)
from .fetcher import fetch_from_source
from .parsers import parse_config
from .testing import process_and_test_proxies


async def run_full_pipeline(
    sources: list[str],
    output_dir: str,
    progress: Progress,
    max_proxies: int | None = None,
    country: str | None = None,
    min_latency: float | None = None,
    max_latency: float | None = None,
):
    """
    Main asynchronous pipeline for fetching, testing, and generating.
    """
    # Step 1: Fetch configurations
    fetched_configs = await _fetch_all_sources(sources, progress)

    if not fetched_configs:
        progress.console.print("[bold red]No configurations fetched. Exiting.[/bold red]")
        return

    progress.console.print(
        f"[bold green]Fetched {len(fetched_configs)} unique configurations.[/bold green]"
    )

    # Limit if requested
    if max_proxies is not None:
        fetched_configs = fetched_configs[:max_proxies]

    # Step 2: Parse and Test configurations
    parsed_proxies = [parse_config(c) for c in fetched_configs]
    valid_proxies = [p for p in parsed_proxies if p is not None]

    tested_proxies = await process_and_test_proxies(valid_proxies, progress)
    working_proxies = [p for p in tested_proxies if p.is_working and p.is_secure]

    progress.console.print(
        f"[bold green]Testing complete. Found {len(working_proxies)} working and secure proxies.[/bold green]"
    )

    # Step 3: Apply filters
    if country:
        working_proxies = [p for p in working_proxies if p.country_code.upper() == country.upper()]
        progress.console.print(
            f"[bold blue]Filtered by country {country.upper()}: {len(working_proxies)} proxies.[/bold blue]"
        )

    if min_latency is not None:
        working_proxies = [p for p in working_proxies if p.latency and p.latency >= min_latency]
        progress.console.print(
            f"[bold blue]Filtered by min latency {min_latency}ms: {len(working_proxies)} proxies.[/bold blue]"
        )

    if max_latency is not None:
        working_proxies = [p for p in working_proxies if p.latency and p.latency <= max_latency]
        progress.console.print(
            f"[bold blue]Filtered by max latency {max_latency}ms: {len(working_proxies)} proxies.[/bold blue]"
        )

    if not working_proxies:
        progress.console.print("[bold yellow]No working proxies after filtering.[/bold yellow]")
        return

    # Step 4: Generate outputs
    _generate_output_files(working_proxies, tested_proxies, output_dir, progress)

    progress.console.print(
        f"[bold blue]All output files generated in '{output_dir}'.[/bold blue]"
    )


async def _fetch_all_sources(sources: list[str], progress: Progress) -> list[str]:
    """Fetch all configurations from sources concurrently."""
    task = progress.add_task("[green]Fetching sources...", total=len(sources))
    all_configs: list[str] = []

    async with aiohttp.ClientSession() as session:
        async def _fetch_and_update(source: str):
            configs = await fetch_from_source(session, source)
            all_configs.extend(configs)
            progress.update(task, advance=1)

        await asyncio.gather(*[_fetch_and_update(s) for s in sources])

    # Remove duplicates
    return list(dict.fromkeys(all_configs))


def _generate_output_files(
    working_proxies: list[Proxy],
    all_proxies: list[Proxy],
    output_dir: str,
    progress: Progress
):
    """Generate all output files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    task = progress.add_task("[blue]Generating output files...", total=6)

    # 1. Base64 subscription
    base64_content = generate_base64_subscription(working_proxies)
    if base64_content:
        (output_path / "vpn_subscription_base64.txt").write_text(
            base64_content, encoding="utf-8"
        )
    progress.update(task, advance=1)

    # 2. Clash configuration
    clash_content = generate_clash_config(working_proxies)
    if clash_content:
        (output_path / "clash.yaml").write_text(clash_content, encoding="utf-8")
    progress.update(task, advance=1)

    # 3. Raw configs
    raw_content = generate_raw_configs(working_proxies)
    if raw_content:
        (output_path / "configs_raw.txt").write_text(raw_content, encoding="utf-8")
    progress.update(task, advance=1)

    # 4. Detailed proxies JSON
    proxies_json = generate_proxies_json(working_proxies)
    if proxies_json:
        (output_path / "proxies.json").write_text(proxies_json, encoding="utf-8")
    progress.update(task, advance=1)

    # 5. Statistics JSON
    stats_json = generate_statistics_json(all_proxies)
    if stats_json:
        (output_path / "statistics.json").write_text(stats_json, encoding="utf-8")
    progress.update(task, advance=1)

    # 6. Metadata with cache-busting
    from datetime import datetime, timezone
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_proxies": len(all_proxies),
        "working_proxies": len(working_proxies),
        "version": "1.0.0"
    }
    (output_path / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    progress.update(task, advance=1)
