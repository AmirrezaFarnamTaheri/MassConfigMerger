import textwrap
from massconfigmerger.advanced_converters import generate_surge_conf, generate_qx_conf



def test_generate_surge_conf_missing_optional():
    proxies = [
        {
            "name": "ws-only",
            "type": "vmess",
            "server": "s.com",
            "port": 443,
            "network": "ws",
        },
        {
            "name": "grpc-only",
            "type": "vless",
            "server": "g.com",
            "port": 443,
            "network": "grpc",
        },
        {
            "type": "ss",
            "server": "x.com",
            "port": 80,
            "cipher": "aes-128-gcm",
            "password": "pass",
        },
    ]
    conf = generate_surge_conf(proxies)
    expected = textwrap.dedent(
        """
        [Proxy]
        ws-only = vmess, s.com, 443, ws=true
        grpc-only = vless, g.com, 443, grpc=true
        proxy = ss, x.com, 80, encrypt-method=aes-128-gcm, password=pass
        """
    ).strip()
    assert conf == expected


def test_generate_qx_conf_missing_optional():
    proxies = [
        {
            "name": "ws-only",
            "type": "vmess",
            "server": "s.com",
            "port": 443,
            "network": "ws",
        },
        {
            "name": "grpc-only",
            "type": "vless",
            "server": "g.com",
            "port": 443,
            "network": "grpc",
        },
        {
            "type": "ss",
            "server": "x.com",
            "port": 80,
            "cipher": "aes-128-gcm",
            "password": "pass",
        },
    ]
    conf = generate_qx_conf(proxies)
    expected = textwrap.dedent(
        """
        vmess=s.com:443, obfs=ws, tag=ws-only
        vless=g.com:443, obfs=grpc, tag=grpc-only
        ss=x.com:80, password=pass, method=aes-128-gcm, tag=proxy
        """
    ).strip()
    assert conf == expected

