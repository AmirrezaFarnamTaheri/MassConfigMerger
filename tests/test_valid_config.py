import base64
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from aggregator_tool import is_valid_config

def test_vmess_with_fragment_accepted():
    data = {"v": "2", "ps": "test"}
    b64 = base64.b64encode(json.dumps(data).encode()).decode().strip("=")
    link = f"vmess://{b64}#note"
    assert is_valid_config(link)


def test_naive_basic_format():
    link = "naive://user:pass@example.com:443"
    assert is_valid_config(link)


def test_hy2_basic_format():
    link = "hy2://uuid@example.com:443"
    assert is_valid_config(link)


def test_wireguard_basic_format():
    link = "wireguard://peer?publicKey=abc"
    assert is_valid_config(link)


def test_trojan_requires_host_port():
    assert is_valid_config("trojan://pass@example.com:443")
    assert not is_valid_config("trojan://pass@example.com")


def test_shadowsocks_requires_host_port():
    assert is_valid_config("ss://method:pw@example.com:8388")
    assert not is_valid_config("ss://method:pw@example.com")


def test_ssr_base64_format():
    raw = "example.com:443:origin:plain:password/"
    b64 = base64.urlsafe_b64encode(raw.encode()).decode().strip("=")
    link = f"ssr://{b64}"
    assert is_valid_config(link)


def test_ssr_with_fragment():
    raw = "example.com:443:origin:plain:password/"
    b64 = base64.urlsafe_b64encode(raw.encode()).decode().strip("=")
    link = f"ssr://{b64}#note"
    assert is_valid_config(link)


def test_shadowtls_basic_format():
    link = "shadowtls://example.com:443"
    assert is_valid_config(link)


def test_brook_basic_format():
    link = "brook://user@example.com:8080"
    assert is_valid_config(link)


def test_juicity_basic_format():
    link = "juicity://pass@example.com:4443"
    assert is_valid_config(link)
