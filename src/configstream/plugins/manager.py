import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Type

from . import Plugin, SourcePlugin, FilterPlugin, ExportPlugin

class PluginManager:
    """Manages plugin lifecycle"""

    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.source_plugins: Dict[str, SourcePlugin] = {}
        self.filter_plugins: Dict[str, FilterPlugin] = {}
        self.export_plugins: Dict[str, ExportPlugin] = {}

    def discover_plugins(self, plugin_dir: Path = None) -> None:
        """Auto-discover plugins from directory"""
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent

        for file in plugin_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue

            module_name = f"configstream.plugins.{file.stem}"
            module = importlib.import_module(module_name)

            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Plugin) and not inspect.isabstract(obj):
                    self.register_plugin(obj)

    def register_plugin(self, plugin_class: Type[Plugin]) -> None:
        """Register a plugin"""
        plugin = plugin_class()
        self.plugins[plugin.name] = plugin

        if isinstance(plugin, SourcePlugin):
            self.source_plugins[plugin.name] = plugin
        elif isinstance(plugin, FilterPlugin):
            self.filter_plugins[plugin.name] = plugin
        elif isinstance(plugin, ExportPlugin):
            self.export_plugins[plugin.name] = plugin

    async def execute_pipeline(
        self,
        source_plugins: List[str],
        filter_plugins: List[str],
        export_plugins: List[str],
        config: Dict[str, Any]
    ) -> None:
        """Execute plugin pipeline"""
        # Fetch from sources
        all_proxies = []
        for plugin_name in source_plugins:
            plugin = self.source_plugins.get(plugin_name)
            if plugin:
                sources = config.get("sources", [])
                if isinstance(sources, list):
                    for source in sources:
                        all_proxies.extend(await plugin.fetch_proxies(source))
                else:
                    all_proxies.extend(await plugin.fetch_proxies(str(sources)))

        # Apply filters
        filtered_proxies = all_proxies
        for plugin_name in filter_plugins:
            plugin = self.filter_plugins.get(plugin_name)
            if plugin:
                filtered_proxies = await plugin.filter_proxies(filtered_proxies)

        # Export results
        for plugin_name in export_plugins:
            plugin = self.export_plugins.get(plugin_name)
            if plugin:
                await plugin.export(filtered_proxies, config.get('output_path'))
