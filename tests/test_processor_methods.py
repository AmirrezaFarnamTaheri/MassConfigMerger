import base64
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from vpn_merger import (
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


def make_trojan(passwd="pw", host="example.com", port=443, note=None):
    link = f"trojan://{passwd}@{host}:{port}"
    if note:
        link += f"#{note}"
    return link


def test_create_semantic_hash_consistent_with_fragment():
    proc = EnhancedConfigProcessor()
    link1 = make_trojan(note=None)
    link2 = make_trojan(note="comment")
    assert proc.create_semantic_hash(link1) == proc.create_semantic_hash(link2)


def test_create_semantic_hash_userid_difference():
    proc = EnhancedConfigProcessor()
    link1 = make_vmess("abc")
    link2 = make_vmess("def")
    assert proc.create_semantic_hash(link1) != proc.create_semantic_hash(link2)


def test_sort_by_performance():
    merger = UltimateVPNMerger()
    r1 = ConfigResult(config="a", protocol="VMess", ping_time=0.5, is_reachable=True)
    r2 = ConfigResult(config="b", protocol="VLESS", ping_time=0.2, is_reachable=True)
    r3 = ConfigResult(config="c", protocol="Reality", ping_time=None, is_reachable=True)
    r4 = ConfigResult(config="d", protocol="Trojan", ping_time=0.1, is_reachable=False)
    ordered = merger._sort_by_performance([r1, r2, r3, r4])
    assert ordered[:3] == [r2, r1, r3]
    assert ordered[-1] == r4


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
