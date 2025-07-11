import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import aggregator_tool


def test_multiple_links_same_line():
    text = "vmess://a vless://b"
    result = aggregator_tool.parse_configs_from_text(text)
    assert "vmess://a" in result
    assert "vless://b" in result
    assert len(result) == 2
