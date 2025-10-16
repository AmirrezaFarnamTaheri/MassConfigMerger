from __future__ import annotations

import asyncio
from pathlib import Path
from rich.progress import Progress

from .di import Container
from .events import EventBus
from .plugins.manager import PluginManager
from .parsers import parse_config
from .proxy_service import ProxyService
from .repositories import InMemoryProxyRepository
from .services import IProxyRepository, IProxyTester
from .testers import SingBoxTester
from .security.advanced_tests import AdvancedSecurityTester
from .benchmarks import ProxyBenchmark


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
    # Setup DI container
    container = Container()
    container.register_singleton(EventBus, EventBus())
    container.register(IProxyRepository, InMemoryProxyRepository)
    container.register(IProxyTester, SingBoxTester)
    container.register(AdvancedSecurityTester)
    container.register(ProxyBenchmark)
    container.register_factory(
        ProxyService,
        lambda c: ProxyService(
            c.resolve(IProxyRepository),
            c.resolve(IProxyTester),
            c.resolve(EventBus),
            c.resolve(AdvancedSecurityTester),
            c.resolve(ProxyBenchmark),
        ),
    )

    plugin_manager = PluginManager()
    plugin_manager.discover_plugins()

    # Step 1: Fetch configurations
    fetched_configs = []
    source_plugin = plugin_manager.source_plugins.get("url_source")
    if source_plugin:
        async def _fetch(source):
            return await source_plugin.fetch_proxies(source)

        results = await asyncio.gather(*[_fetch(s) for s in sources])
        for result in results:
            fetched_configs.extend(result)

    if not fetched_configs:
        progress.console.print("[bold red]No configurations fetched. Exiting.[/bold red]")
        return

    # Step 2: Parse and process proxies
    parsed_proxies = [parse_config(c) for c in fetched_configs if c]
    valid_proxies = [p for p in parsed_proxies if p is not None]

    proxy_service = container.resolve(ProxyService)

    semaphore = asyncio.Semaphore(50) # Limit concurrent processing
    async def process_proxy_task(proxy):
        async with semaphore:
            await proxy_service.process_proxy(proxy)

    await asyncio.gather(*[process_proxy_task(p) for p in valid_proxies])

    # Step 3: Get results from repository
    proxy_repo = container.resolve(IProxyRepository)
    all_proxies = await proxy_repo.get_all()
    working_proxies = [p for p in all_proxies if p.is_working and p.is_secure]

    # Step 4: Apply filters
    if country:
        country_filter_plugin = plugin_manager.filter_plugins.get("country_filter")
        if country_filter_plugin:
            from .plugins.default_plugins import CountryFilterPlugin
            working_proxies = await CountryFilterPlugin(country).filter_proxies(working_proxies)

    if max_latency is not None:
        latency_filter_plugin = plugin_manager.filter_plugins.get("latency_filter")
        if latency_filter_plugin:
            from .plugins.default_plugins import LatencyFilterPlugin
            working_proxies = await LatencyFilterPlugin(max_latency).filter_proxies(working_proxies)


    # Step 5: Generate outputs
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    export_plugins = [
        "base64_export",
        "clash_export",
        "raw_export",
        "proxies_json_export",
        "stats_json_export",
    ]

    for plugin_name in export_plugins:
        plugin = plugin_manager.export_plugins.get(plugin_name)
        if plugin:
            await plugin.export(working_proxies, output_path)

    progress.console.print(
        f"[bold blue]All output files generated in '{output_dir}'.[/bold blue]"
    )