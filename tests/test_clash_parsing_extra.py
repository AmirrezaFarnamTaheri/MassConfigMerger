import os
import sys
import base64

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from clash_utils import config_to_clash_proxy


def test_ssr_parse_success():
    raw = "example.com:443:origin:aes-128-gcm:plain:cGFzcw==/?remarks=bmFtZQ==&obfsparam=c2FsdA==&protoparam=YXV0aA=="
    b64 = base64.urlsafe_b64encode(raw.encode()).decode().strip("=")
    link = f"ssr://{b64}"
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["type"] == "ssr"
    assert proxy["server"] == "example.com"
    assert proxy["port"] == 443
    assert proxy["cipher"] == "aes-128-gcm"
    assert proxy["password"] == "pass"
    assert proxy["protocol"] == "origin"
    assert proxy["obfs"] == "plain"
    assert proxy["obfs-param"] == "salt"
    assert proxy["protocol-param"] == "auth"
    assert proxy["name"] == "name"


def test_ssr_parse_invalid():
    assert config_to_clash_proxy("ssr://invalid", 0) is None


def test_reality_parse_extra():
    link = (
        "reality://uuid@host:443?flow=xtls-rprx-vision&pbk=pub&sid=123"
        "&sni=example.com&fp=chrome#test"
    )
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["type"] == "vless"
    assert proxy["tls"] is True
    assert proxy["flow"] == "xtls-rprx-vision"
    assert proxy["pbk"] == "pub"
    assert proxy["sid"] == "123"
    assert proxy["sni"] == "example.com"
    assert proxy["fp"] == "chrome"
    assert proxy["name"] == "test"


def test_hysteria2_parse():
    link = "hy2://pass@host:443?peer=example.com&insecure=1"
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["type"] == "hysteria2"
    assert proxy["server"] == "host"
    assert proxy["port"] == 443
    assert proxy["password"] == "pass"
    assert proxy["peer"] == "example.com"
    assert proxy["insecure"] == "1"


def test_hysteria2_invalid():
    assert config_to_clash_proxy("hy2://host", 0) is None


def test_tuic_parse():
    link = "tuic://uuid:pw@host:443?alpn=h3"
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["type"] == "tuic"
    assert proxy["uuid"] == "uuid"
    assert proxy["password"] == "pw"
    assert proxy["alpn"] == "h3"
