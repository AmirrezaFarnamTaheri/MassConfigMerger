import base64

from massconfigmerger import aggregator_tool


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


def test_parse_oversized_line(caplog):
    big_line = "A" * (aggregator_tool.MAX_DECODE_SIZE + 1)
    with caplog.at_level('DEBUG'):
        result = aggregator_tool.parse_configs_from_text(big_line)
    assert result == set()
    assert "Skipping oversized base64 line" in caplog.text


def test_urlsafe_base64_line():
    encoded = base64.urlsafe_b64encode(b"vmess://a  >").decode()
    result = aggregator_tool.parse_configs_from_text(encoded)
    assert result == {"vmess://a"}
