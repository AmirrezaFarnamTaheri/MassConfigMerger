from __future__ import annotations

import asyncio
from pathlib import Path

import aiohttp
from rich.progress import Progress

from .core import (
    Proxy,
    fetch_from_source,
    process_and_test_proxies,
    generate_base64_subscription,
    generate_clash_config,
    generate_raw_configs,
)


async def run_full_pipeline(sources: list[str], output_dir: str, progress: Progress):
    """
    The main asynchronous pipeline for fetching, testing, and generating.
    """
    # Step 1: Fetch configurations from all sources
    fetched_configs = await _fetch_all_sources(sources, progress)
    if not fetched_configs:
        progress.console.print("[bold red]No configurations were fetched. Exiting.[/bold red]")
        return

    progress.console.print(
        f"[bold green]Successfully fetched {len(fetched_configs)} unique configurations.[/bold green]"
    )

    # Step 2: Test all fetched configurations
    tested_proxies = await process_and_test_proxies(fetched_configs, progress)
    working_proxies = [p for p in tested_proxies if p.is_working]
    progress.console.print(
        f"[bold green]Testing complete. Found {len(working_proxies)} working proxies.[/bold green]"
    )

    if not working_proxies:
        progress.console.print("[bold yellow]No working proxies found. No files will be generated.[/bold yellow]")
        return

    # Step 3: Generate the output files
    _generate_output_files(tested_proxies, output_dir, progress)
    progress.console.print(
        f"[bold blue]Output files have been generated in '{output_dir}'.[/bold blue]"
    )


async def _fetch_all_sources(sources: list[str], progress: Progress) -> list[str]:
    """
    Fetches all configurations from the given sources concurrently.
    """
    task = progress.add_task("[green]Fetching sources...", total=len(sources))
    all_configs: list[str] = []

    async with aiohttp.ClientSession() as session:

        async def _fetch_and_update(source: str):
            configs = await fetch_from_source(session, source)
            all_configs.extend(configs)
            progress.update(task, advance=1)

        await asyncio.gather(*[_fetch_and_update(s) for s in sources])

    # Remove duplicate configurations
    return list(dict.fromkeys(all_configs))


def _generate_output_files(proxies: list[Proxy], output_dir: str, progress: Progress):
    """
    Generates all output files from the tested proxies.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    task = progress.add_task("[blue]Generating output files...", total=3)

    # Generate Base64 subscription file (for V2Ray, etc.)
    base64_content = generate_base64_subscription(proxies)
    if base64_content:
        (output_path / "vpn_subscription_base64.txt").write_text(
            base64_content, encoding="utf-8"
        )
    progress.update(task, advance=1)

    # Generate Clash configuration file
    clash_content = generate_clash_config(proxies)
    if clash_content:
        (output_path / "clash.yaml").write_text(clash_content, encoding="utf-8")
    progress.update(task, advance=1)

    # Generate raw configs file
    raw_content = generate_raw_configs(proxies)
    if raw_content:
        (output_path / "configs_raw.txt").write_text(raw_content, encoding="utf-8")
    progress.update(task, advance=1)