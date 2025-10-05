"""Utility converters for additional client formats.

This module contains helpers for generating configuration snippets for
other popular VPN clients such as Surge and Quantumult X. Both
functions accept a list of Clash-style proxy dictionaries and return a
string ready to be written to a configuration file.
"""

__all__ = ["generate_surge_conf", "generate_qx_conf"]

from typing import Any, Dict, List


def generate_surge_conf(proxies: List[Dict[str, Any]]) -> str:
    """Return a Surge `[Proxy]` configuration block for ``proxies``.

    Each proxy dictionary should follow the Clash format produced by
    :func:`massconfigmerger.clash_utils.config_to_clash_proxy`.
    Only common options are included to keep the output broadly
    compatible with modern Surge versions.
    """
    lines = ["[Proxy]"]
    for p in proxies:
        name = p.get("name", "proxy")
        typ = p.get("type", "http")
        server = p.get("server", "")
        port = p.get("port", 0)
        line = f"{name} = {typ}, {server}, {port}"
        if p.get("uuid"):
            line += f", username={p['uuid']}"
        if p.get("password") and typ != "ss":
            line += f", password={p['password']}"
        if p.get("cipher") and typ == "ss":
            line += f", encrypt-method={p['cipher']}"
            if p.get("password"):
                line += f", password={p['password']}"
        if p.get("tls"):
            line += ", tls=true"
        if p.get("sni"):
            line += f", sni={p['sni']}"
        net = p.get("network")
        if net == "ws":
            line += ", ws=true"
            if p.get("path"):
                line += f", ws-path={p['path']}"
            if p.get("host"):
                line += f", ws-headers=Host:{p['host']}"
        if net == "grpc":
            line += ", grpc=true"
            if p.get("serviceName"):
                line += f", grpc-service-name={p['serviceName']}"
        lines.append(line)
    return "\n".join(lines)


def generate_qx_conf(proxies: List[Dict[str, Any]]) -> str:
    """Return Quantumult X server lines for ``proxies``."""
    lines = []
    for p in proxies:
        typ = p.get("type", "http")
        server = p.get("server", "")
        port = p.get("port", 0)
        base = f"{typ}={server}:{port}"
        params = []
        if p.get("uuid"):
            params.append(f"id={p['uuid']}")
        if p.get("password"):
            params.append(f"password={p['password']}")
        if p.get("cipher"):
            params.append(f"method={p['cipher']}")
        if p.get("tls"):
            params.append("tls=true")
        if p.get("sni"):
            params.append(f"tls-host={p['sni']}")
        net = p.get("network")
        if net == "ws":
            params.append("obfs=ws")
            if p.get("host"):
                params.append(f"obfs-host={p['host']}")
            if p.get("path"):
                params.append(f"obfs-uri={p['path']}")
        if net == "grpc":
            params.append("obfs=grpc")
            if p.get("serviceName"):
                params.append(f"grpc-service-name={p['serviceName']}")
        params.append(f"tag={p.get('name', 'proxy')}")
        lines.append(base + ", " + ", ".join(params))
    return "\n".join(lines)
