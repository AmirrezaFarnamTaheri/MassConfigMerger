from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .common import sanitize_headers, sanitize_str


def _parse_reality_opts(q: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to parse and build the reality-opts dictionary."""
    pbk_q = q.get("pbk") or q.get("public-key") or q.get("publicKey") or q.get("public_key") or q.get("publickey")
    sid_q = q.get("sid") or q.get("short-id") or q.get("shortId") or q.get("short_id") or q.get("shortid")
    spider_q = q.get("spiderX") or q.get("spider-x") or q.get("spider_x")

    pbk = sanitize_str(pbk_q[0]) if pbk_q is not None else None
    sid = sanitize_str(sid_q[0]) if sid_q is not None else None
    spider = sanitize_str(spider_q[0]) if spider_q is not None else None

    opts = {}
    if pbk is not None:
        opts["public-key"] = pbk
    if sid is not None:
        opts["short-id"] = sid
    if spider is not None:
        opts["spider-x"] = spider

    return opts, pbk, sid, spider


def parse(config: str, idx: int) -> Optional[Dict[str, Any]]:
    """
    Parse a VLESS configuration link.

    Args:
        config: The VLESS configuration link.
        idx: The index of the configuration, used for default naming.

    Returns:
        A dictionary representing the Clash proxy, or None if parsing fails.
    """
    p = urlparse(config)
    q = parse_qs(p.query)
    name = sanitize_str(p.fragment or f"vless-{idx}")
    security = q.get("security")
    proxy = {
        "name": name,
        "type": "vless",
        "server": sanitize_str(p.hostname or ""),
        "port": p.port or 0,
        "uuid": sanitize_str(p.username or ""),
        "encryption": sanitize_str(q.get("encryption", ["none"])[0]),
    }
    if security:
        proxy["tls"] = True
    net = q.get("type") or q.get("mode")
    if net:
        proxy["network"] = sanitize_str(net[0])
    for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
        if q.get(key) is not None:
            proxy[key] = sanitize_str(q[key][0])

    reality_opts, pbk, sid, spider = _parse_reality_opts(q)
    if pbk is not None:
        proxy["pbk"] = pbk
    if sid is not None:
        proxy["sid"] = sid
    if spider is not None:
        proxy["spiderX"] = spider
    if reality_opts:
        proxy["reality-opts"] = reality_opts

    if "ws-headers" in q:
        proxy["ws-headers"] = sanitize_headers(q["ws-headers"][0])
    return proxy


def parse_reality(config: str, idx: int) -> Optional[Dict[str, Any]]:
    """
    Parse a Reality configuration link.

    Args:
        config: The Reality configuration link.
        idx: The index of the configuration, used for default naming.

    Returns:
        A dictionary representing the Clash proxy, or None if parsing fails.
    """
    p = urlparse(config)
    q = parse_qs(p.query)
    name = sanitize_str(p.fragment or f"reality-{idx}")
    proxy = {
        "name": name,
        "type": "vless",
        "server": sanitize_str(p.hostname or ""),
        "port": p.port or 0,
        "uuid": sanitize_str(p.username or ""),
        "encryption": sanitize_str(q.get("encryption", ["none"])[0]),
        "tls": True,
    }
    for key in ("sni", "alpn", "fp", "serviceName", "flow", "host", "path"):
        if q.get(key) is not None:
            proxy[key] = sanitize_str(q[key][0])

    reality_opts, pbk, sid, spider = _parse_reality_opts(q)
    if pbk is not None:
        proxy["pbk"] = pbk
    if sid is not None:
        proxy["sid"] = sid
    if spider is not None:
        proxy["spiderX"] = spider
    if reality_opts:
        proxy["reality-opts"] = reality_opts

    net = q.get("type") or q.get("mode")
    if net:
        proxy["network"] = sanitize_str(net[0])

    if "ws-headers" in q:
        proxy["ws-headers"] = sanitize_headers(q["ws-headers"][0])
    return proxy
