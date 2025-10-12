import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from configstream.plugins.manager import PluginManager
from configstream.plugins.base import ParserPlugin, OutputPlugin, FilterPlugin, TestPlugin, PluginMetadata


class SampleParser(ParserPlugin):
    @property
    def metadata(self):
        return PluginMetadata("sample-parser", "1.0", "tester", "a sample parser")

    def can_parse(self, config: str) -> bool:
        return config.startswith("sample://")

    def parse(self, config: str) -> dict:
        return {"protocol": "sample"}


class SampleOutput(OutputPlugin):
    @property
    def metadata(self):
        return PluginMetadata("sample-output", "1.0", "tester", "a sample output")

    @property
    def file_extension(self):
        return ".sample"

    def format(self, nodes: list) -> str:
        return ""


class SampleFilter(FilterPlugin):
    @property
    def metadata(self):
        return PluginMetadata("sample-filter", "1.0", "tester", "a sample filter")

    def filter(self, node: dict) -> bool:
        return True


class SampleTest(TestPlugin):
    @property
    def metadata(self):
        return PluginMetadata("sample-test", "1.0", "tester", "a sample test")

    async def test(self, node: dict) -> dict:
        return {"tested": True}


@pytest.fixture
def plugin_manager() -> PluginManager:
    """Fixture for PluginManager."""
    return PluginManager()


def test_register_plugins(plugin_manager: PluginManager):
    """Test registering plugins."""
    plugin_manager.register_parser(SampleParser())
    plugin_manager.register_output(SampleOutput())
    plugin_manager.register_filter(SampleFilter())
    plugin_manager.register_test(SampleTest())

    assert len(plugin_manager.get_parsers()) == 1
    assert len(plugin_manager.get_outputs()) == 1
    assert len(plugin_manager.get_filters()) == 1
    assert len(plugin_manager.get_tests()) == 1


def test_discover_plugins(plugin_manager: PluginManager, tmp_path: Path):
    """Test discovering plugins from a directory."""
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    plugin_file = plugin_dir / "sample_plugin.py"
    plugin_file.write_text(
        """
from configstream.plugins.base import ParserPlugin, PluginMetadata

class DiscoveredParser(ParserPlugin):
    @property
    def metadata(self):
        return PluginMetadata("discovered-parser", "1.0", "tester", "a discovered parser")

    def can_parse(self, config: str) -> bool:
        return True

    def parse(self, config: str) -> dict:
        return {}
"""
    )

    plugin_manager.discover_plugins(plugin_dirs=[plugin_dir])

    assert len(plugin_manager.get_parsers()) == 1
    assert plugin_manager.get_parsers()[0].metadata.name == "discovered-parser"


def test_find_parser(plugin_manager: PluginManager):
    """Test finding a parser."""
    plugin_manager.register_parser(SampleParser())
    parser = plugin_manager.find_parser("sample://test")
    assert parser is not None
    assert parser.metadata.name == "sample-parser"


def test_get_output_by_name(plugin_manager: PluginManager):
    """Test getting an output plugin by name."""
    plugin_manager.register_output(SampleOutput())
    output = plugin_manager.get_output_by_name("sample-output")
    assert output is not None
    assert output.metadata.name == "sample-output"
