import pytest
from configstream.plugins.base import ParserPlugin, OutputPlugin


# Concrete implementation for ParserPlugin for testing purposes
class MyTestParser(ParserPlugin):
    def can_parse(self, config: str) -> bool:
        return config.startswith("myprotocol://")

    def parse(self, config: str) -> dict:
        if self.can_parse(config):
            return {"protocol": "myprotocol", "data": config.split("://")[1]}
        return {}


# Concrete implementation for OutputPlugin for testing purposes
class MyTestOutput(OutputPlugin):
    def format(self, nodes: list) -> str:
        return "\n".join([node.get("data", "") for node in nodes])


def test_parser_plugin_implementation():
    """Test that a concrete implementation of ParserPlugin can be instantiated."""
    parser = MyTestParser()
    assert parser.can_parse("myprotocol://test")
    assert not parser.can_parse("otherprotocol://test")
    assert parser.parse("myprotocol://test-data") == {
        "protocol": "myprotocol",
        "data": "test-data",
    }
    assert parser.parse("other://test") == {}


def test_output_plugin_implementation():
    """Test that a concrete implementation of OutputPlugin can be instantiated."""
    output = MyTestOutput()
    nodes = [
        {"protocol": "myprotocol", "data": "data1"},
        {"protocol": "myprotocol", "data": "data2"},
    ]
    assert output.format(nodes) == "data1\ndata2"


def test_abstract_methods_not_implemented():
    """Test that instantiating without implementing abstract methods raises TypeError."""
    with pytest.raises(TypeError):

        class BadParser(ParserPlugin):
            pass

        BadParser()

    with pytest.raises(TypeError):

        class BadOutput(OutputPlugin):
            pass

        BadOutput()


class CoveringParser(ParserPlugin):
    def can_parse(self, config: str) -> bool:
        super().can_parse(config)
        return False

    def parse(self, config: str) -> dict:
        super().parse(config)
        return {}


class CoveringOutput(OutputPlugin):
    def format(self, nodes: list) -> str:
        super().format(nodes)
        return ""


def test_calling_super_on_abstract_methods():
    """Test that calling super() on abstract methods does not raise an error and improves coverage."""
    parser = CoveringParser()
    parser.can_parse("test")
    parser.parse("test")

    output = CoveringOutput()
    output.format([])