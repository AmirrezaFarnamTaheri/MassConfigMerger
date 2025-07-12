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


def test_extract_all_protocols():
    text = " ".join(
        [
            "vmess://a",
            "vless://b",
            "reality://c",
            "ss://d",
            "ssr://e",
            "trojan://f",
            "hy2://g",
            "hysteria://h",
            "hysteria2://i",
            "tuic://j",
            "naive://k",
            "juicity://l",
            "brook://m",
            "shadowtls://n",
            "wireguard://o",
        ]
    )
    result = aggregator_tool.parse_configs_from_text(text)
    assert len(result) == 15
    for item in text.split():
        assert item in result
