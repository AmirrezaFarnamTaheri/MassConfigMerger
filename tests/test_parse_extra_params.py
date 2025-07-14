from massconfigmerger.vpn_merger import UltimateVPNMerger


def test_parse_extra_params_reality():
    merger = UltimateVPNMerger()
    link = (
        "reality://id@host:443?public_key=pub&shortid=42"
        "&spider-x=spin"
    )
    result = merger._parse_extra_params(link)
    assert result["publicKey"] == "pub"
    assert result["shortId"] == "42"
    assert result["spiderX"] == "spin"


def test_parse_extra_params_tuic():
    merger = UltimateVPNMerger()
    link = (
        "tuic://uuid:pw@host:443?alpn=h3&congestion_control=bbr"
        "&udp_relay_mode=native"
    )
    result = merger._parse_extra_params(link)
    assert result["uuid"] == "uuid"
    assert result["password"] == "pw"
    assert result["alpn"] == "h3"
    assert result["congestion-control"] == "bbr"
    assert result["udp-relay-mode"] == "native"


def test_parse_extra_params_hysteria2():
    merger = UltimateVPNMerger()
    link = (
        "hy2://pass@host:443?auth=none&peer=ex.com&sni=site.com&insecure=1"
        "&alpn=h3&obfs=ob&obfs-password=opw&up=5&downmbps=10"
    )
    result = merger._parse_extra_params(link)
    assert result["password"] == "pass"
    assert result["auth"] == "none"
    assert result["peer"] == "ex.com"
    assert result["sni"] == "site.com"
    assert result["insecure"] == "1"
    assert result["alpn"] == "h3"
    assert result["obfs"] == "ob"
    assert result["obfs_password"] == "opw"
    assert result["upmbps"] == "5"
    assert result["downmbps"] == "10"
