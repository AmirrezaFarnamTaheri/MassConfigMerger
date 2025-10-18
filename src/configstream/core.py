"""Core proxy testing and parsing logic"""

import asyncio
import base64
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import yaml


@dataclass
class Proxy:
    """Proxy configuration model"""

    config: str
    protocol: str
    address: str
    port: int
    uuid: str = ""
    remarks: str = ""
    country: str = ""
    country_code: str = ""
    city: str = ""
    asn: str = ""
    asn_number: str = ""
    latency: float | None = None
    is_working: bool = False
    is_secure: bool = True
    security_issues: list[str] = field(default_factory=list)
    tested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _details: dict[str, Any] = field(default_factory=dict)
    security: str = "auto"


class ProxyTester:
    """Tests proxy connectivity"""

    def __init__(self,
                 timeout: int = 10,
                 test_url: str = "http://www.gstatic.com/generate_204"):
        self.timeout = timeout
        self.test_url = test_url

    async def test(self, proxy: Proxy) -> Proxy:
        """Test proxy connectivity"""
        import aiohttp
        from aiohttp_proxy import ProxyConnector

        connector = ProxyConnector.from_url(proxy.config)
        start_time = asyncio.get_running_loop().time()
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(self.test_url,
                                       timeout=self.timeout) as response:
                    if 200 <= response.status < 300:
                        proxy.is_working = True
                        end_time = asyncio.get_running_loop().time()
                        proxy.latency = (end_time - start_time) * 1000  # in ms
        except Exception:
            proxy.is_working = False
        finally:
            proxy.tested_at = datetime.now(timezone.utc).isoformat()
            await connector.close()
            return proxy


async def run_single_proxy_test(config: str,
                                timeout: int = 10) -> Proxy | None:
    """Test a single proxy configuration"""
    proxy = parse_config(config)
    if proxy:
        tester = ProxyTester(timeout)
        return await tester.test(proxy)
    return None


def parse_config(config: str) -> Proxy | None:
    """Parse proxy configuration string"""
    try:
        if config.startswith("vmess://"):
            return _parse_vmess(config)
        elif config.startswith("vless://"):
            return _parse_vless(config)
        elif config.startswith("ss://"):
            return _parse_shadowsocks(config)
        elif config.startswith("trojan://"):
            return _parse_trojan(config)
    except Exception:
        return None


def _parse_vmess(config: str) -> Proxy | None:
    """Parse VMess configuration"""
    try:
        data = config[len("vmess://"):]
        # Normalize padding
        pad_len = (-len(data)) % 4
        if pad_len:
            data += "=" * pad_len
        decoded_bytes = None
        try:
            decoded_bytes = base64.b64decode(data)
        except Exception:
            # Try URL-safe base64
            decoded_bytes = base64.urlsafe_b64decode(data)
        decoded = decoded_bytes.decode("utf-8", errors="ignore")
        vmess_data = json.loads(decoded)

        return Proxy(
            config=config,
            protocol="vmess",
            address=vmess_data.get("add", ""),
            port=int(vmess_data.get("port", 443)),
            uuid=vmess_data.get("id", ""),
            remarks=vmess_data.get("ps", ""),
            _details=vmess_data,
        )
    except Exception:
        return None


def _parse_vless(config: str) -> Proxy | None:
    """Parse VLESS configuration"""
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None
        query = parse_qs(parsed.query)

        return Proxy(
            config=config,
            protocol="vless",
            address=parsed.hostname,
            port=parsed.port or 443,
            uuid=parsed.username or "",
            remarks=unquote(parsed.fragment or ""),
            _details={
                k: v[0]
                for k, v in query.items()
            },
        )
    except Exception:
        return None


def _parse_shadowsocks(config: str) -> Proxy | None:
    """Parse Shadowsocks configuration"""
    try:
        # Handle ss://<base64>@host:port#remark format
        if "@" in config:
            encoded_part, host_part = config.replace("ss://", "").split("@", 1)
            host, port_remark = host_part.split(":", 1)
            port, remark_part = (port_remark.split("#", 1)
                                 if "#" in port_remark else (port_remark, ""))

            decoded_user_info = base64.b64decode(encoded_part).decode("utf-8")
            method, password = decoded_user_info.split(":", 1)
        else:
            # Fallback for other potential formats, though less common
            return None

        proxy = Proxy(
            config=config,
            protocol="shadowsocks",
            address=host,
            port=int(port),
            uuid="",  # Not used for shadowsocks
            remarks=unquote(remark_part or ""),
        )
        proxy._details["method"] = method
        proxy._details["password"] = password
        return proxy
    except Exception:
        return None


def _parse_trojan(config: str) -> Proxy | None:
    """Parse Trojan configuration"""
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None
        return Proxy(
            config=config,
            protocol="trojan",
            address=parsed.hostname,
            port=parsed.port or 443,
            uuid=parsed.username or "",
            remarks=unquote(parsed.fragment or ""),
        )
    except Exception:
        return None


def geolocate_proxy(proxy: Proxy, geoip_reader=None) -> Proxy:
    """
    Add geolocation data to proxy.
    Gracefully handles missing GeoIP database.
    """
    if geoip_reader is None:
        # GeoIP not available - set defaults
        proxy.country = "Unknown"
        proxy.country_code = "XX"
        proxy.city = "Unknown"
        proxy.asn = "Unknown"
        return proxy

    try:
        # Use geoip_reader to lookup address
        response = geoip_reader.city(proxy.address)
        proxy.country = response.country.name or "Unknown"
        proxy.country_code = response.country.iso_code or "XX"
        proxy.city = response.city.name or "Unknown"
        proxy.asn = (f"AS{response.autonomous_system_number}"
                     if response.autonomous_system_number else "Unknown")

    except Exception:
        # GeoIP lookup failed - set defaults
        proxy.country = "Unknown"
        proxy.country_code = "XX"
        proxy.city = "Unknown"
        proxy.asn = "Unknown"

    return proxy


# Export functions for generating output formats
def generate_base64_subscription(proxies: list[Proxy]) -> str:
    """Generate base64 subscription"""
    configs = [p.config for p in proxies if p.is_working]
    return base64.b64encode("\n".join(configs).encode()).decode()


def generate_clash_config(proxies: list[Proxy]) -> str:
    """Generate Clash configuration"""
    clash_proxies = []
    for p in proxies:
        if p.is_working:
            proxy_data = {
                "name": p.remarks or f"{p.protocol}-{p.address}",
                "type": p.protocol,
                "server": p.address,
                "port": p.port,
                "uuid": p.uuid,
            }
            # Add protocol-specific fields
            if p.protocol in ["vmess", "vless"]:
                proxy_data.update({
                    "alterId": p._details.get("aid", 0),
                    "cipher": p._details.get("scy", "auto"),
                    "tls": p._details.get("tls", "") == "tls",
                    "network": p._details.get("net", "tcp"),
                })
            elif p.protocol == "shadowsocks":
                proxy_data.update({
                    "cipher": p._details.get("method"),
                    "password": p._details.get("password"),
                })

            clash_proxies.append(proxy_data)

    return yaml.dump({
        "proxies":
        clash_proxies,
        "proxy-groups": [{
            "name": "🚀 ConfigStream",
            "type": "select",
            "proxies": [p["name"] for p in clash_proxies],
        }],
    })
