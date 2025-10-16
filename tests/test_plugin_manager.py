import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from src.configstream.plugins import Plugin, SourcePlugin, FilterPlugin, ExportPlugin
from src.configstream.plugins.manager import PluginManager


class MockSourcePlugin(SourcePlugin):
    @property
    def name(self):
        return "mock_source"
    @property
    def version(self):
        return "1.0.0"
    async def initialize(self, config):
        pass
    async def execute(self, context):
        return {}
    async def fetch_proxies(self, url):
        return []

class MockFilterPlugin(FilterPlugin):
    @property
    def name(self):
        return "mock_filter"
    @property
    def version(self):
        return "1.0.0"
    async def initialize(self, config):
        pass
    async def execute(self, context):
        return {}
    async def filter_proxies(self, proxies):
        return []

class MockExportPlugin(ExportPlugin):
    @property
    def name(self):
        return "mock_export"
    @property
    def version(self):
        return "1.0.0"
    async def initialize(self, config):
        pass
    async def execute(self, context):
        return {}
    async def export(self, proxies, output_path):
        pass

def test_plugin_manager_discover_and_register():
    """Test that the plugin manager can discover and register plugins."""
    manager = PluginManager()

    # Create a mock plugin file
    plugin_content = """
from src.configstream.plugins import SourcePlugin

class TestSourcePlugin(SourcePlugin):
    @property
    def name(self):
        return "test_source"
    @property
    def version(self):
        return "1.0.0"
    async def initialize(self, config):
        pass
    async def execute(self, context):
        return {}
    async def fetch_proxies(self, url):
        return []
"""
    plugin_dir = Path("src/configstream/plugins")
    (plugin_dir / "test_source_plugin.py").write_text(plugin_content)

    manager.discover_plugins()

    assert "test_source" in manager.plugins
    assert "test_source" in manager.source_plugins

    # Clean up the mock plugin file
    (plugin_dir / "test_source_plugin.py").unlink()


def test_plugin_manager_register():
    """Test that the plugin manager can register plugins."""
    manager = PluginManager()
    manager.register_plugin(MockSourcePlugin)
    manager.register_plugin(MockFilterPlugin)
    manager.register_plugin(MockExportPlugin)

    assert "mock_source" in manager.plugins
    assert "mock_source" in manager.source_plugins
    assert "mock_filter" in manager.plugins
    assert "mock_filter" in manager.filter_plugins
    assert "mock_export" in manager.plugins
    assert "mock_export" in manager.export_plugins

@pytest.mark.asyncio
async def test_plugin_manager_execute_pipeline():
    """Test that the plugin manager can execute a pipeline."""
    manager = PluginManager()

    # Register mock plugins
    mock_source = MockSourcePlugin()
    mock_filter = MockFilterPlugin()
    mock_export = MockExportPlugin()

    mock_source.fetch_proxies = AsyncMock(return_value=["proxy1"])
    mock_filter.filter_proxies = AsyncMock(return_value=["proxy1"])
    mock_export.export = AsyncMock()

    manager.source_plugins["mock_source"] = mock_source
    manager.filter_plugins["mock_filter"] = mock_filter
    manager.export_plugins["mock_export"] = mock_export

    await manager.execute_pipeline(
        source_plugins=["mock_source"],
        filter_plugins=["mock_filter"],
        export_plugins=["mock_export"],
        config={"sources": ["http://test.com"], "output_path": Path("/tmp")}
    )

    mock_source.fetch_proxies.assert_called_once_with(["http://test.com"])
    mock_filter.filter_proxies.assert_called_once_with(["proxy1"])
    mock_export.export.assert_called_once_with(["proxy1"], Path("/tmp"))