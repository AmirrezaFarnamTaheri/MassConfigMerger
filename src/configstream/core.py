"""Core proxy testing and parsing logic"""

import asyncio
import base64
import json
import yaml
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs, unquote

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
    latency: Optional[float] = None
    is_working: bool = False
    is_secure: bool = True
    security_issues: List[str] = field(default_factory=list)
    tested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _details: Dict[str, Any] = field(default_factory=dict)
    security: str = "auto"

class ProxyTester:
    """Tests proxy connectivity"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def test(self, proxy: Proxy) -> Proxy:
        """Test proxy connectivity"""
        try:
            # Simulate testing (replace with actual implementation)
            await asyncio.sleep(0.1)
            proxy.is_working = True
            proxy.latency = 100.0
            proxy.tested_at = datetime.now(timezone.utc).isoformat()
            return proxy
        except Exception:
            proxy.is_working = False
            return proxy

async def test_proxy(config: str, timeout: int = 10) -> Optional[Proxy]:
    """Test a single proxy configuration"""
    proxy = parse_config(config)
    if proxy:
        tester = ProxyTester(timeout)
        return await tester.test(proxy)
    return None

def parse_config(config: str) -> Optional[Proxy]:
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
        else:
            # Generic parse
            parsed = urlparse(config)
            return Proxy(
                config=config,
                protocol=parsed.scheme,
                address=parsed.hostname or "",
                port=parsed.port or 443,
                uuid=parsed.username or "",
                remarks=unquote(parsed.fragment or "")
            )
    except Exception:
        return None

def _parse_vmess(config: str) -> Optional[Proxy]:
    """Parse VMess configuration"""
    try:
        # Remove vmess:// prefix
        data = config.replace("vmess://", "")
        # Decode base64
        decoded = base64.b64decode(data).decode('utf-8')
        vmess_data = json.loads(decoded)

        return Proxy(
            config=config,
            protocol="vmess",
            address=vmess_data.get("add", ""),
            port=int(vmess_data.get("port", 443)),
            uuid=vmess_data.get("id", ""),
            remarks=vmess_data.get("ps", ""),
            _details=vmess_data
        )
    except Exception:
        return None

def _parse_vless(config: str) -> Optional[Proxy]:
    """Parse VLESS configuration"""
    try:
        parsed = urlparse(config)
        query = parse_qs(parsed.query)

        return Proxy(
            config=config,
            protocol="vless",
            address=parsed.hostname or "",
            port=parsed.port or 443,
            uuid=parsed.username or "",
            remarks=unquote(parsed.fragment or ""),
            _details={k: v[0] for k, v in query.items()}
        )
    except Exception:
        return None

def _parse_shadowsocks(config: str) -> Optional[Proxy]:
    """Parse Shadowsocks configuration"""
    try:
        parsed = urlparse(config)
        return Proxy(
            config=config,
            protocol="shadowsocks",
            address=parsed.hostname or "",
            port=parsed.port or 443,
            uuid="",
            remarks=unquote(parsed.fragment or "")
        )
    except Exception:
        return None

def _parse_trojan(config: str) -> Optional[Proxy]:
    """Parse Trojan configuration"""
    try:
        parsed = urlparse(config)
        return Proxy(
            config=config,
            protocol="trojan",
            address=parsed.hostname or "",
            port=parsed.port or 443,
            uuid=parsed.username or "",
            remarks=unquote(parsed.fragment or "")
        )
    except Exception:
        return None

# Export functions for generating output formats
def generate_base64_subscription(proxies: List[Proxy]) -> str:
    """Generate base64 subscription"""
    configs = [p.config for p in proxies if p.is_working]
    return base64.b64encode("\n".join(configs).encode()).decode()

def generate_clash_config(proxies: List[Proxy]) -> str:
    """Generate Clash configuration"""
    clash_proxies = []
    for p in proxies:
        if p.is_working:
            clash_proxies.append({
                "name": p.remarks or f"{p.protocol}-{p.address}",
                "type": p.protocol,
                "server": p.address,
                "port": p.port
            })

    return yaml.dump({
        "proxies": clash_proxies,
        "proxy-groups": [{
            "name": "ConfigStream",
            "type": "select",
            "proxies": [p["name"] for p in clash_proxies]
        }]
    })
