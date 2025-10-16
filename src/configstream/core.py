from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar

import aiohttp
import yaml


@dataclass
class Proxy:
    """Represents a parsed and testable proxy configuration."""

    config: str
    protocol: str = "unknown"
    is_working: bool = False
    latency: float | None = None
    country: str = "Unknown"
    country_code: str = "XX"
    asn: str = "Unknown"
    asn_number: int | None = None
    city: str = "Unknown"

    # Security flags
    is_secure: bool = True
    security_issues: list[str] = field(default_factory=list)

    # Performance metrics
    jitter: float | None = None
    packet_loss: float = 0.0
    bandwidth_score: float | None = None

    # Parsed fields
    remarks: str = ""
    address: str = ""
    port: int = 0
    uuid: str = ""
    security: str = "auto"

    # Additional metadata
    _details: dict = field(default_factory=dict)
    tested_at: str = ""

    _test_cache: ClassVar[dict[str, "Proxy"]] = {}


def generate_base64_subscription(proxies: list[Proxy]) -> str:
    """Generate Base64 subscription."""
    working = [p.config for p in proxies if p.is_working and p.is_secure]
    if not working:
        return ""
    combined = "\n".join(working)
    return base64.b64encode(combined.encode("utf-8")).decode("utf-8")


def generate_clash_config(proxies: list[Proxy]) -> str:
    """Generate Clash configuration."""
    proxy_list = []

    for proxy in (p for p in proxies if p.is_working and p.is_secure):
        clash_proxy = None

        if proxy.protocol == "vmess":
            clash_proxy = {
                "name": proxy.remarks or f"vmess-{proxy.address}",
                "type": "vmess",
                "server": proxy.address,
                "port": proxy.port,
                "uuid": proxy.uuid,
                "alterId": proxy._details.get("aid", 0),
                "cipher": proxy.security,
                "tls": proxy._details.get("tls") == "tls",
                "network": proxy._details.get("net", "tcp"),
            }
        elif proxy.protocol == "vless":
            clash_proxy = {
                "name": proxy.remarks or f"vless-{proxy.address}",
                "type": "vless",
                "server": proxy.address,
                "port": proxy.port,
                "uuid": proxy.uuid,
                "tls": proxy._details.get("security") == "tls",
                "network": proxy._details.get("type", "tcp"),
            }
        elif proxy.protocol == "shadowsocks":
            clash_proxy = {
                "name": proxy.remarks or f"ss-{proxy.address}",
                "type": "ss",
                "server": proxy.address,
                "port": proxy.port,
                "cipher": proxy._details.get("method"),
                "password": proxy._details.get("password"),
            }
        elif proxy.protocol == "trojan":
            clash_proxy = {
                "name": proxy.remarks or f"trojan-{proxy.address}",
                "type": "trojan",
                "server": proxy.address,
                "port": proxy.port,
                "password": proxy.uuid,
                "sni": proxy._details.get("sni", ""),
            }

        if clash_proxy:
            proxy_list.append(clash_proxy)

    if not proxy_list:
        return ""

    config = {
        "proxies": proxy_list,
        "proxy-groups": [
            {
                "name": "🚀 ConfigStream",
                "type": "select",
                "proxies": [p["name"] for p in proxy_list],
            },
            {
                "name": "♻️ Auto Select",
                "type": "url-test",
                "proxies": [p["name"] for p in proxy_list],
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
            },
        ],
        "rules": [
            "MATCH,🚀 ConfigStream"
        ],
    }

    return yaml.dump(config, sort_keys=False, allow_unicode=True, indent=2)


def generate_raw_configs(proxies: list[Proxy]) -> str:
    """Generate raw configuration list."""
    return "\n".join([p.config for p in proxies if p.is_working and p.is_secure])


def generate_proxies_json(proxies: list[Proxy]) -> str:
    """Generate detailed JSON with proxy information."""
    proxy_data = []

    for p in proxies:
        if p.is_working and p.is_secure:
            proxy_data.append({
                "protocol": p.protocol,
                "remarks": p.remarks or f"{p.protocol}-{p.address}",
                "address": p.address,
                "port": p.port,
                "latency": p.latency,
                "is_secure": p.is_secure,
                "security_issues": p.security_issues,
                "tested_at": p.tested_at,
                "config": p.config,
                "location": {
                    "country": p.country,
                    "country_code": p.country_code,
                    "city": p.city,
                    "asn": {
                        "name": p.asn,
                        "number": p.asn_number,
                    },
                },
            })

    return json.dumps(proxy_data, indent=2, ensure_ascii=False)


def generate_statistics_json(proxies: list[Proxy]) -> str:
    """Generate statistics JSON."""
    working = [p for p in proxies if p.is_working and p.is_secure]

    # Protocol distribution
    protocols: dict[str, int] = {}
    for p in working:
        protocols[p.protocol] = protocols.get(p.protocol, 0) + 1

    # Country distribution
    countries: dict[str, int] = {}
    for p in working:
        countries[p.country_code] = countries.get(p.country_code, 0) + 1

    # Latency stats
    latencies = [p.latency for p in working if p.latency is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    stats = {
        "total_tested": len(proxies),
        "working": len(working),
        "failed": len(proxies) - len(working),
        "success_rate": round(len(working) / len(proxies) * 100, 2) if proxies else 0,
        "average_latency": round(avg_latency, 2),
        "protocols": protocols,
        "countries": countries,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    return json.dumps(stats, indent=2)