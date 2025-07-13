import base64

from massconfigmerger.clash_utils import config_to_clash_proxy


def test_ssr_parse_success():
    raw = (
        "example.com:443:origin:aes-128-gcm:plain:cGFzcw==/"
        "?remarks=bmFtZQ==&obfsparam=c2FsdA==&protoparam=YXV0aA=="
        "&udpport=53&uot=1&group=Z3Jw"
    )
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
    assert proxy["udpport"] == 53
    assert proxy["uot"] == "1"
    assert proxy["group"] == "grp"


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
    link = "hy2://pass@host:443?peer=example.com&insecure=1&upmbps=10&downmbps=20"
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["type"] == "hysteria2"
    assert proxy["server"] == "host"
    assert proxy["port"] == 443
    assert proxy["password"] == "pass"
    assert proxy["peer"] == "example.com"
    assert proxy["insecure"] == "1"
    assert proxy["upmbps"] == "10"
    assert proxy["downmbps"] == "20"


def test_hysteria2_invalid():
    assert config_to_clash_proxy("hy2://host", 0) is None


def test_tuic_parse():
    link = "tuic://uuid:pw@host:443?alpn=h3"
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["type"] == "tuic"
    assert proxy["uuid"] == "uuid"
    assert proxy["password"] == "pw"
    assert proxy["alpn"] == "h3"


def test_vless_parse_ws_headers():
    headers = base64.urlsafe_b64encode(b'{"h": "v"}').decode().strip("=")
    link = (
        "vless://uuid@host:443?type=ws&host=ex.com&path=/a"
        f"&ws-headers={headers}&serviceName=s"
    )
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["network"] == "ws"
    assert proxy["ws-headers"]["h"] == "v"
    assert proxy["serviceName"] == "s"


def test_trojan_parse_extra():
    link = (
        "trojan://pw@host:443?type=ws&host=example.com&path=/ws"
        "&alpn=h2&flow=xtls-rprx-udp&serviceName=svc"
        "&ws-headers="
        + base64.urlsafe_b64encode(b'{"X-Test": "val"}').decode().strip("=")
    )
    proxy = config_to_clash_proxy(link, 0)
    assert proxy["type"] == "trojan"
    assert proxy["network"] == "ws"
    assert proxy["host"] == "example.com"
    assert proxy["path"] == "/ws"
    assert proxy["alpn"] == "h2"
    assert proxy["flow"] == "xtls-rprx-udp"
    assert proxy["serviceName"] == "svc"
    assert proxy["ws-headers"]["X-Test"] == "val"
