import asyncio
import base64
import json
import sys
import types

from massconfigmerger.vpn_merger import (
    EnhancedConfigProcessor,
    ConfigResult,
    UltimateVPNMerger,
    CONFIG,
)


def make_vmess(id_value, host="example.com", port=443, note=None):
    data = {"add": host, "port": port, "id": id_value}
    b64 = base64.b64encode(json.dumps(data).encode()).decode().strip("=")
    link = f"vmess://{b64}"
    if note:
        link += f"#{note}"
    return link


def make_vmess_from_dict(data, note=None):
    b64 = base64.b64encode(json.dumps(data).encode()).decode().strip("=")
    link = f"vmess://{b64}"
    if note:
        link += f"#{note}"
    return link


def make_trojan(passwd="pw", host="example.com", port=443, note=None):
    link = f"trojan://{passwd}@{host}:{port}"
    if note:
        link += f"#{note}"
    return link


def make_trojan_userpass(user="user", passwd="pw", host="example.com", port=443, note=None):
    link = f"trojan://{user}:{passwd}@{host}:{port}"
    if note:
        link += f"#{note}"
    return link


def make_shadowsocks(password="pw", host="example.com", port=443, note=None, method="aes-128-gcm"):
    payload = f"{method}:{password}@{host}:{port}"
    b64 = base64.b64encode(payload.encode()).decode().strip("=")
    link = f"ss://{b64}"
    if note:
        link += f"#{note}"
    return link


def make_shadowsocksr(host="example.com", port=443):
    raw = f"{host}:{port}:origin:plain:password/"
    b64 = base64.urlsafe_b64encode(raw.encode()).decode().strip("=")
    return f"ssr://{b64}"


def test_create_semantic_hash_consistent_with_fragment():
    proc = EnhancedConfigProcessor()
    link1 = make_trojan(note=None)
    link2 = make_trojan(note="comment")
    assert proc.create_semantic_hash(link1) == proc.create_semantic_hash(link2)


def test_create_semantic_hash_query_param_order():
    proc = EnhancedConfigProcessor()
    link1 = "foo://example.com/path?a=1&b=2#frag"
    link2 = "foo://example.com/path?b=2&a=1"
    assert proc.create_semantic_hash(link1) == proc.create_semantic_hash(link2)


def test_create_semantic_hash_duplicate_params_and_fragment():
    proc = EnhancedConfigProcessor()
    link1 = "foo://example.com/path?a=1&a=2&b=3#frag"
    link2 = "foo://example.com/path?a=2&a=1&b=3"
    assert proc.create_semantic_hash(link1) == proc.create_semantic_hash(link2)


def test_create_semantic_hash_fragment_ignored_generic():
    proc = EnhancedConfigProcessor()
    link1 = "foo://example.com/path?a=1&b=2"
    link2 = "foo://example.com/path?a=1&b=2#extra"
    assert proc.create_semantic_hash(link1) == proc.create_semantic_hash(link2)


def test_create_semantic_hash_vmess_key_order():
    proc = EnhancedConfigProcessor()
    d1 = {"add": "ex.com", "port": 80, "id": "abc"}
    d2 = {"id": "abc", "add": "ex.com", "port": 80}
    link1 = make_vmess_from_dict(d1)
    link2 = make_vmess_from_dict(d2)
    assert proc.create_semantic_hash(link1) == proc.create_semantic_hash(link2)


def test_create_semantic_hash_trojan_query_param_order():
    proc = EnhancedConfigProcessor()
    link1 = "trojan://pw@example.com:443?a=1&b=2"
    link2 = "trojan://pw@example.com:443?b=2&a=1#foo"
    assert proc.create_semantic_hash(link1) == proc.create_semantic_hash(link2)


def test_create_semantic_hash_userid_difference():
    proc = EnhancedConfigProcessor()
    link1 = make_vmess("abc")
    link2 = make_vmess("def")
    assert proc.create_semantic_hash(link1) != proc.create_semantic_hash(link2)


def test_create_semantic_hash_trojan_password_difference():
    proc = EnhancedConfigProcessor()
    link1 = make_trojan(passwd="one")
    link2 = make_trojan(passwd="two")
    assert proc.create_semantic_hash(link1) != proc.create_semantic_hash(link2)


def test_create_semantic_hash_trojan_userinfo_difference():
    proc = EnhancedConfigProcessor()
    link1 = make_trojan_userpass(user="user", passwd="one")
    link2 = make_trojan_userpass(user="user", passwd="two")
    assert proc.create_semantic_hash(link1) != proc.create_semantic_hash(link2)


def test_create_semantic_hash_shadowsocks_password_difference():
    proc = EnhancedConfigProcessor()
    link1 = make_shadowsocks(password="one")
    link2 = make_shadowsocks(password="two")
    assert proc.create_semantic_hash(link1) != proc.create_semantic_hash(link2)


def test_extract_host_port_ssr():
    proc = EnhancedConfigProcessor()
    link = make_shadowsocksr(host="h.example", port=1234)
    host, port = proc.extract_host_port(link)
    assert host == "h.example"
    assert port == 1234


def test_sort_by_performance():
    merger = UltimateVPNMerger()
    r1 = ConfigResult(config="a", protocol="VMess", ping_time=0.5, is_reachable=True)
    r2 = ConfigResult(config="b", protocol="VLESS", ping_time=0.2, is_reachable=True)
    r3 = ConfigResult(config="c", protocol="Reality", ping_time=None, is_reachable=True)
    r4 = ConfigResult(config="d", protocol="Trojan", ping_time=0.1, is_reachable=False)
    ordered = merger._sort_by_performance([r1, r2, r3, r4])
    assert ordered[:3] == [r2, r1, r3]
    assert ordered[-1] == r4


def test_sort_by_reliability(monkeypatch):
    monkeypatch.setattr(CONFIG, "sort_by", "reliability")
    merger = UltimateVPNMerger()
    r1 = ConfigResult(config="a", protocol="VMess", ping_time=0.5, is_reachable=True)
    r2 = ConfigResult(config="b", protocol="VMess", ping_time=0.2, is_reachable=True)
    r3 = ConfigResult(config="c", protocol="VMess", ping_time=0.1, is_reachable=True)

    h1 = merger.processor.create_semantic_hash("a")
    h2 = merger.processor.create_semantic_hash("b")
    merger.proxy_history = {
        h1: {
            "successful_checks": 1,
            "total_checks": 2,
            "last_latency_ms": None,
            "last_seen_online_utc": None,
        },
        h2: {
            "successful_checks": 1,
            "total_checks": 5,
            "last_latency_ms": None,
            "last_seen_online_utc": None,
        },
    }

    ordered = merger._sort_by_performance([r1, r2, r3])
    assert ordered[0] == r1
    assert ordered[1] == r2


def test_sort_by_reliability_latency_tiebreak(monkeypatch):
    monkeypatch.setattr(CONFIG, "sort_by", "reliability")
    merger = UltimateVPNMerger()
    r1 = ConfigResult(config="a", protocol="VMess", ping_time=0.2, is_reachable=True)
    r2 = ConfigResult(config="b", protocol="VMess", ping_time=0.3, is_reachable=True)

    h1 = merger.processor.create_semantic_hash("a")
    h2 = merger.processor.create_semantic_hash("b")
    # equal reliability -> order by latency
    merger.proxy_history = {
        h1: {
            "successful_checks": 1,
            "total_checks": 2,
            "last_latency_ms": None,
            "last_seen_online_utc": None,
        },
        h2: {
            "successful_checks": 1,
            "total_checks": 2,
            "last_latency_ms": None,
            "last_seen_online_utc": None,
        },
    }

    ordered = merger._sort_by_performance([r2, r1])
    assert ordered[0] == r1
    assert ordered[1] == r2


def test_deduplicate_config_results(monkeypatch):
    merger = UltimateVPNMerger()
    monkeypatch.setattr(CONFIG, "tls_fragment", None)
    monkeypatch.setattr(CONFIG, "include_protocols", None)
    monkeypatch.setattr(CONFIG, "exclude_protocols", None)

    link1 = make_trojan()
    link2 = make_trojan(note="foo")
    link3 = make_trojan(host="other.com")
    r1 = ConfigResult(config=link1, protocol="Trojan")
    r2 = ConfigResult(config=link2, protocol="Trojan")
    r3 = ConfigResult(config=link3, protocol="Trojan")
    unique = merger._deduplicate_config_results([r1, r2, r3])
    assert len(unique) == 2
    hashes = [merger.processor.create_semantic_hash(r.config) for r in unique]
    assert len(set(hashes)) == 2


def test_deduplicate_config_results_password_difference(monkeypatch):
    merger = UltimateVPNMerger()
    monkeypatch.setattr(CONFIG, "tls_fragment", None)
    monkeypatch.setattr(CONFIG, "include_protocols", None)
    monkeypatch.setattr(CONFIG, "exclude_protocols", None)

    link1 = make_trojan(passwd="a")
    link2 = make_trojan(passwd="b")
    r1 = ConfigResult(config=link1, protocol="Trojan")
    r2 = ConfigResult(config=link2, protocol="Trojan")
    unique = merger._deduplicate_config_results([r1, r2])
    assert len(unique) == 2
    assert set(r.config for r in unique) == {link1, link2}


def test_deduplicate_config_results_userinfo_password(monkeypatch):
    merger = UltimateVPNMerger()
    monkeypatch.setattr(CONFIG, "tls_fragment", None)
    monkeypatch.setattr(CONFIG, "include_protocols", None)
    monkeypatch.setattr(CONFIG, "exclude_protocols", None)

    link1 = make_trojan_userpass(passwd="a")
    link2 = make_trojan_userpass(passwd="b")
    r1 = ConfigResult(config=link1, protocol="Trojan")
    r2 = ConfigResult(config=link2, protocol="Trojan")
    unique = merger._deduplicate_config_results([r1, r2])
    assert len(unique) == 2
    assert set(r.config for r in unique) == {link1, link2}


def test_print_final_summary_zero_configs(capsys):
    """Ensure summary handles empty results gracefully."""
    merger = UltimateVPNMerger()
    stats = {
        "protocol_stats": {},
        "performance_stats": {},
        "total_configs": 0,
        "reachable_configs": 0,
        "available_sources": 0,
        "total_sources": 0,
    }

    merger._print_final_summary(0, 0.5, stats)
    captured = capsys.readouterr().out
    assert "Success rate: N/A" in captured
    assert "Top protocol: N/A" in captured


def test_lookup_country(monkeypatch):
    proc = EnhancedConfigProcessor()
    monkeypatch.setattr(CONFIG, "geoip_db", "dummy.mmdb")

    class DummyCountry:
        iso_code = "US"

    class DummyReader:
        def __init__(self, path):
            pass

        def country(self, ip):
            return types.SimpleNamespace(country=DummyCountry())

    dummy_geoip2 = types.ModuleType("geoip2")
    dummy_database = types.ModuleType("geoip2.database")
    dummy_database.Reader = DummyReader
    dummy_geoip2.database = dummy_database
    monkeypatch.setitem(sys.modules, "geoip2", dummy_geoip2)
    monkeypatch.setitem(sys.modules, "geoip2.database", dummy_database)

    assert asyncio.run(proc.lookup_country("1.2.3.4")) == "US"


def test_deduplicate_semantic_equivalent(monkeypatch):
    """Ensure deduplication relies on semantic hashes, not raw strings."""
    merger = UltimateVPNMerger()
    monkeypatch.setattr(CONFIG, "tls_fragment", None)
    monkeypatch.setattr(CONFIG, "include_protocols", None)
    monkeypatch.setattr(CONFIG, "exclude_protocols", None)

    base = make_vmess("id1", host="h.example", port=80)
    uri = "vmess://id1@h.example:80?type=ws"
    r1 = ConfigResult(config=base, protocol="VMess", host="h.example", port=80)
    r2 = ConfigResult(config=uri, protocol="VMess", host="h.example", port=80)

    unique = merger._deduplicate_config_results([r1, r2])
    assert len(unique) == 1
    assert unique[0].config in {base, uri}


def test_country_filters(monkeypatch):
    merger = UltimateVPNMerger()
    monkeypatch.setattr(CONFIG, "tls_fragment", None)
    monkeypatch.setattr(CONFIG, "include_protocols", None)
    monkeypatch.setattr(CONFIG, "exclude_protocols", None)

    r1 = ConfigResult(config="a", protocol="VMess", country="US")
    r2 = ConfigResult(config="b", protocol="VMess", country="FR")

    monkeypatch.setattr(CONFIG, "include_countries", {"US"})
    monkeypatch.setattr(CONFIG, "exclude_countries", None)
    unique = merger._deduplicate_config_results([r1, r2])
    assert [u.config for u in unique] == ["a"]

    monkeypatch.setattr(CONFIG, "include_countries", None)
    monkeypatch.setattr(CONFIG, "exclude_countries", {"FR"})
    unique = merger._deduplicate_config_results([r1, r2])
    assert {u.config for u in unique} == {"a"}


def test_country_filters_no_geoip(monkeypatch):
    """Configs should not be filtered when GeoIP info is missing."""
    merger = UltimateVPNMerger()
    monkeypatch.setattr(CONFIG, "tls_fragment", None)
    monkeypatch.setattr(CONFIG, "include_protocols", None)
    monkeypatch.setattr(CONFIG, "exclude_protocols", None)

    r1 = ConfigResult(config="a", protocol="VMess", country=None)
    r2 = ConfigResult(config="b", protocol="VMess", country=None)

    monkeypatch.setattr(CONFIG, "include_countries", {"US"})
    monkeypatch.setattr(CONFIG, "exclude_countries", None)
    unique = merger._deduplicate_config_results([r1, r2])
    assert {u.config for u in unique} == {"a", "b"}

    monkeypatch.setattr(CONFIG, "include_countries", None)
    monkeypatch.setattr(CONFIG, "exclude_countries", {"CN"})
    unique = merger._deduplicate_config_results([r1, r2])
    assert {u.config for u in unique} == {"a", "b"}
