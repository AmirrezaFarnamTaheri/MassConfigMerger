import textwrap
from massconfigmerger.advanced_converters import (
    generate_surge_conf,
    generate_qx_conf,
    generate_xyz_conf,
)


def test_generate_surge_conf():
    proxies = [
        {
            "name": "ws",
            "type": "vmess",
            "server": "s.com",
            "port": 443,
            "uuid": "id",
            "tls": True,
            "network": "ws",
            "host": "h",
            "path": "/ws",
        },
        {
            "name": "grpc",
            "type": "vless",
            "server": "g.com",
            "port": 443,
            "uuid": "id2",
            "tls": True,
            "network": "grpc",
            "serviceName": "sn",
        },
    ]
    conf = generate_surge_conf(proxies)
    expected = textwrap.dedent(
        """
        [Proxy]
        ws = vmess, s.com, 443, username=id, tls=true, ws=true, ws-path=/ws, ws-headers=Host:h
        grpc = vless, g.com, 443, username=id2, tls=true, grpc=true, grpc-service-name=sn
        """
    ).strip()
    assert conf == expected


def test_generate_qx_conf():
    proxies = [
        {
            "name": "ws",
            "type": "vmess",
            "server": "s.com",
            "port": 443,
            "uuid": "id",
            "tls": True,
            "network": "ws",
            "host": "h",
            "path": "/ws",
        },
        {
            "name": "grpc",
            "type": "vless",
            "server": "g.com",
            "port": 443,
            "uuid": "id2",
            "tls": True,
            "network": "grpc",
            "serviceName": "sn",
        },
    ]
    conf = generate_qx_conf(proxies)
    expected = textwrap.dedent(
        """
        vmess=s.com:443, id=id, tls=true, obfs=ws, obfs-host=h, obfs-uri=/ws, tag=ws
        vless=g.com:443, id=id2, tls=true, obfs=grpc, grpc-service-name=sn, tag=grpc
        """
    ).strip()
    assert conf == expected


def test_generate_xyz_conf():
    proxies = [
        {"name": "a", "type": "vmess", "server": "s.com", "port": 1},
        {"name": "b", "type": "trojan", "server": "t.com", "port": 2},
    ]
    conf = generate_xyz_conf(proxies)
    expected = textwrap.dedent(
        """
        a|s.com|1|vmess
        b|t.com|2|trojan
        """
    ).strip()
    assert conf == expected
