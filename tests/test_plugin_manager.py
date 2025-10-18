import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from configstream.plugins import (ExportPlugin, FilterPlugin, Plugin,
                                  SourcePlugin)
from configstream.plugins.manager import PluginManager


# Dummy Plugins for Testing
class DummySourcePlugin(SourcePlugin):
    name = "dummy_source"
    version = "0.1.0"

    async def initialize(self, config):
        pass

    async def execute(self, context):
        return context

    async def fetch_proxies(self, source: str):
        return [f"proxy_from_{source}"]


class DummyFilterPlugin(FilterPlugin):
    name = "dummy_filter"
    version = "0.1.0"

    async def initialize(self, config):
        pass

    async def execute(self, context):
        return context

    async def filter_proxies(self, proxies: list):
        return [p for p in proxies if "special" in p]


class DummyExportPlugin(ExportPlugin):
    name = "dummy_export"
    version = "0.1.0"

    async def initialize(self, config):
        pass

    async def execute(self, context):
        return context

    async def export(self, proxies: list, output_path: Path):
        pass  # No-op for testing


class TestPluginManager(unittest.TestCase):

    def setUp(self):
        self.manager = PluginManager()

    def test_register_plugin(self):
        self.manager.register_plugin(DummySourcePlugin)
        self.assertIn("dummy_source", self.manager.plugins)
        self.assertIn("dummy_source", self.manager.source_plugins)

    @patch("importlib.import_module")
    def test_discover_plugins(self, mock_import_module):
        # Create a dummy plugin file for discovery
        plugin_dir = Path(__file__).parent / "dummy_plugins"
        plugin_dir.mkdir(exist_ok=True)
        (plugin_dir / "my_plugin.py").write_text(
            "from configstream.plugins import Plugin\n"
            "class MyDiscoveredPlugin(Plugin):\n"
            "    name = 'discovered'\n"
            "    version = '0.1.0'\n"
            "    async def initialize(self, config): pass\n"
            "    async def execute(self, context): return context\n")

        # Mock the import to return a module with the plugin class
        mock_module = MagicMock()

        class MyDiscoveredPlugin(Plugin):
            name = "discovered"
            version = "0.1.0"

            async def initialize(self, config):
                pass

            async def execute(self, context):
                return context

        mock_module.MyDiscoveredPlugin = MyDiscoveredPlugin
        mock_import_module.return_value = mock_module

        self.manager.discover_plugins(plugin_dir)
        mock_import_module.assert_called_with("configstream.plugins.my_plugin")

        # Clean up the dummy plugin file
        (plugin_dir / "my_plugin.py").unlink()
        plugin_dir.rmdir()

    def test_execute_pipeline(self):
        asyncio.run(self.execute_pipeline_async())

    async def execute_pipeline_async(self):
        # Register mock plugins
        source_plugin = DummySourcePlugin()
        filter_plugin = DummyFilterPlugin()
        export_plugin = DummyExportPlugin()

        source_plugin.fetch_proxies = AsyncMock(
            return_value=["proxy1_special", "proxy2"])
        filter_plugin.filter_proxies = AsyncMock(
            side_effect=lambda proxies: [p for p in proxies if "special" in p])
        export_plugin.export = AsyncMock()

        self.manager.source_plugins["dummy_source"] = source_plugin
        self.manager.filter_plugins["dummy_filter"] = filter_plugin
        self.manager.export_plugins["dummy_export"] = export_plugin

        config = {"sources": ["source1"], "output_path": Path("/tmp/output")}

        await self.manager.execute_pipeline(
            source_plugins=["dummy_source"],
            filter_plugins=["dummy_filter"],
            export_plugins=["dummy_export"],
            config=config,
        )

        source_plugin.fetch_proxies.assert_called_once_with("source1")
        filter_plugin.filter_proxies.assert_called_once_with(
            ["proxy1_special", "proxy2"])
        export_plugin.export.assert_called_once_with(["proxy1_special"],
                                                     Path("/tmp/output"))


if __name__ == "__main__":
    unittest.main()
