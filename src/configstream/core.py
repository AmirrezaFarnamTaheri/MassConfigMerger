from __future__ import annotations

import asyncio
import base64
import json
import hashlib
import socket
import ssl
from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import parse_qs, unquote, urlparse
from datetime import datetime

import aiohttp
import yaml
from aiohttp_proxy import ProxyConnector
from rich.progress import Progress
import geoip2.database
from singbox2proxy import SingBoxProxy

# Configuration
TEST_URL = "https://www.google.com/generate_204"
TEST_TIMEOUT = 10
SECURITY_CHECK_TIMEOUT = 5

# Security test endpoints
SECURITY_TESTS = {
    "redirect": "http://httpbin.org/redirect/1",
    "headers": "http://httpbin.org/headers",
    "content": "http://example.com",
    "ssl": "https://www.howsmyssl.com/a/check",
}


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

    @classmethod
    def from_config(cls, config: str) -> "Proxy" | None:
        """Parse a raw proxy configuration string."""
        if config.startswith("vmess://"):
            return cls._parse_vmess(config)
        elif config.startswith("vless://"):
            return cls._parse_vless(config)
        elif config.startswith("ss://"):
            return cls._parse_ss(config)
        elif config.startswith("trojan://"):
            return cls._parse_trojan(config)
        elif config.startswith("hy2://") or config.startswith("hysteria2://"):
            return cls._parse_hysteria2(config)
        elif config.startswith("hysteria://"):
            return cls._parse_hysteria(config)
        elif config.startswith("tuic://"):
            return cls._parse_tuic(config)
        elif config.startswith("wg://") or config.startswith("wireguard://"):
            return cls._parse_wireguard(config)
        elif any(config.startswith(f"{p}://") for p in ["ssh", "http", "https", "socks", "socks4", "socks5"]):
            return cls._parse_generic(config)
        elif config.startswith("naive+https://"):
            return cls._parse_naive(config)
        return None

    @staticmethod
    def _parse_naive(config: str) -> "Proxy" | None:
        """Parse naive+https:// URI."""
        try:
            parsed = urlparse(config.replace("naive+", ""))
            query = parse_qs(parsed.query)

            return Proxy(
                config=config,
                protocol="naive",
                remarks=unquote(parsed.fragment or ""),
                address=parsed.hostname or "",
                port=parsed.port or 443,
                uuid=parsed.username or "",
                _details={k: v[0] for k, v in query.items()},
            )
        except Exception:
            return None

    @staticmethod
    def _parse_wireguard(config: str) -> "Proxy" | None:
        """Parse wireguard:// URI."""
        try:
            parsed = urlparse(config)
            query = parse_qs(parsed.query)

            return Proxy(
                config=config,
                protocol="wireguard",
                remarks=unquote(parsed.fragment or ""),
                address=parsed.hostname or "",
                port=parsed.port or 51820,
                _details={k: v[0] for k, v in query.items()},
            )
        except Exception:
            return None

    @staticmethod
    def _parse_hysteria2(config: str) -> "Proxy" | None:
        """Parse hy2:// or hysteria2:// URI."""
        try:
            parsed = urlparse(config)
            query = parse_qs(parsed.query)

            return Proxy(
                config=config,
                protocol="hysteria2",
                remarks=unquote(parsed.fragment or ""),
                address=parsed.hostname or "",
                port=parsed.port or 443,
                uuid=parsed.username or "",
                _details={k: v[0] for k, v in query.items()},
            )
        except Exception:
            return None

    @staticmethod
    def _parse_hysteria(config: str) -> "Proxy" | None:
        """Parse hysteria:// URI."""
        try:
            parsed = urlparse(config)
            query = parse_qs(parsed.query)

            return Proxy(
                config=config,
                protocol="hysteria",
                remarks=unquote(parsed.fragment or ""),
                address=parsed.hostname or "",
                port=parsed.port or 443,
                uuid=parsed.username or "",
                _details={k: v[0] for k, v in query.items()},
            )
        except Exception:
            return None

    @staticmethod
    def _parse_tuic(config: str) -> "Proxy" | None:
        """Parse tuic:// URI."""
        try:
            parsed = urlparse(config)
            query = parse_qs(parsed.query)

            # TUIC format: tuic://uuid:password@server:port
            uuid_pass = parsed.username
            uuid = uuid_pass.split(':')[0] if uuid_pass and ':' in uuid_pass else uuid_pass

            return Proxy(
                config=config,
                protocol="tuic",
                remarks=unquote(parsed.fragment or ""),
                address=parsed.hostname or "",
                port=parsed.port or 443,
                uuid=uuid or "",
                _details={k: v[0] for k, v in query.items()},
            )
        except Exception:
            return None

    @staticmethod
    def _parse_generic(config: str) -> "Proxy" | None:
        """Parse generic URI format."""
        try:
            parsed = urlparse(config)
            query = parse_qs(parsed.query)

            return Proxy(
                config=config,
                protocol=parsed.scheme,
                remarks=unquote(parsed.fragment or ""),
                address=parsed.hostname or "",
                port=parsed.port or 0,
                uuid=parsed.username or "",
                _details={k: v[0] for k, v in query.items()},
            )
        except Exception:
            return None

    @staticmethod
    def _parse_trojan(config: str) -> "Proxy" | None:
        """Parse trojan:// URI."""
        try:
            parsed = urlparse(config)
            query = parse_qs(parsed.query)

            return Proxy(
                config=config,
                protocol="trojan",
                remarks=unquote(parsed.fragment or ""),
                address=parsed.hostname or "",
                port=parsed.port or 443,
                uuid=parsed.username or "",
                _details={k: v[0] for k, v in query.items()},
            )
        except Exception:
            return None

    @staticmethod
    def _parse_ss(config: str) -> "Proxy" | None:
        """Parse ss:// URI."""
        try:
            parsed = urlparse(config)

            encoded = parsed.username or ""
            padded = encoded + '=' * (-len(encoded) % 4)
            decoded = base64.b64decode(padded).decode("utf-8")

            if ":" not in decoded:
                return None

            method, password = decoded.split(":", 1)

            return Proxy(
                config=config,
                protocol="shadowsocks",
                remarks=unquote(parsed.fragment or ""),
                address=parsed.hostname or "",
                port=parsed.port or 8388,
                _details={"method": method, "password": password},
            )
        except Exception:
            return None

    @staticmethod
    def _parse_vless(config: str) -> "Proxy" | None:
        """Parse vless:// URI."""
        try:
            parsed = urlparse(config)
            query = parse_qs(parsed.query)

            return Proxy(
                config=config,
                protocol="vless",
                remarks=unquote(parsed.fragment or ""),
                address=parsed.hostname or "",
                port=parsed.port or 443,
                uuid=parsed.username or "",
                _details={k: v[0] for k, v in query.items()},
            )
        except Exception:
            return None

    @staticmethod
    def _parse_vmess(config: str) -> "Proxy" | None:
        """Parse vmess:// URI."""
        try:
            encoded = config[len("vmess://"):]
            padded = encoded + '=' * (-len(encoded) % 4)
            decoded = base64.b64decode(padded).decode("utf-8")
            details = json.loads(decoded)

            return Proxy(
                config=config,
                protocol="vmess",
                remarks=details.get("ps", ""),
                address=details.get("add", ""),
                port=int(details.get("port", 0)),
                uuid=details.get("id", ""),
                security=details.get("scy", "auto"),
                _details=details,
            )
        except Exception:
            return None

    @classmethod
    async def test(cls, proxy_instance: "Proxy", worker: "SingBoxWorker") -> "Proxy":
        """Test a proxy configuration."""
        if proxy_instance.config in cls._test_cache:
            return cls._test_cache[proxy_instance.config]

        proxy_instance.tested_at = datetime.utcnow().isoformat() + "Z"

        # Geolocate
        await cls._geolocate(proxy_instance)

        # Test connectivity and security
        try:
            await worker.test_proxy(proxy_instance)
        except Exception as e:
            proxy_instance.is_working = False
            proxy_instance.security_issues.append(f"Test failed: {str(e)}")

        cls._test_cache[proxy_instance.config] = proxy_instance
        return proxy_instance

    @staticmethod
    async def _geolocate(proxy: "Proxy"):
        """Get geolocation info for proxy."""
        try:
            with geoip2.database.Reader("data/GeoLite2-Country.mmdb") as reader:
                response = reader.country(proxy.address)
                proxy.country = response.country.name or "Unknown"
                proxy.country_code = response.country.iso_code or "XX"
        except Exception:
            pass

        try:
            with geoip2.database.Reader("data/GeoLite2-City.mmdb") as reader:
                response = reader.city(proxy.address)
                proxy.city = response.city.name or "Unknown"
        except Exception:
            pass

        try:
            with geoip2.database.Reader("data/ip-to-asn.mmdb") as reader:
                response = reader.asn(proxy.address)
                proxy.asn_number = response.autonomous_system_number
                proxy.asn = f"AS{response.autonomous_system_number} ({response.autonomous_system_organization})"
        except Exception:
            pass


class SingBoxWorker:
    """Worker managing sing-box process for testing proxies."""

    def __init__(self):
        self.proxy: SingBoxProxy | None = None
        self.session: aiohttp.ClientSession | None = None
        self.connector: ProxyConnector | None = None

    async def start(self):
        """Start the sing-box worker."""
        # Worker will be started per-proxy for now
        # TODO: Implement persistent worker in future optimization
        pass

    async def stop(self):
        """Stop the sing-box worker."""
        if self.session:
            await self.session.close()
            self.session = None
        if self.proxy:
            await self.proxy.stop()
            self.proxy = None

    async def test_proxy(self, proxy_instance: Proxy):
        """Test a single proxy configuration."""
        self.proxy = SingBoxProxy(proxy_instance.config)
        await self.proxy.start()

        try:
            self.connector = ProxyConnector.from_url(self.proxy.http_proxy_url)
            self.session = aiohttp.ClientSession(connector=self.connector)

            # Basic connectivity test
            start_time = asyncio.get_event_loop().time()
            async with self.session.get(TEST_URL, timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)) as response:
                if response.status == 204:
                    end_time = asyncio.get_event_loop().time()
                    proxy_instance.latency = round((end_time - start_time) * 1000, 2)
                    proxy_instance.is_working = True
                else:
                    proxy_instance.is_working = False
                    return

            # Security tests (non-blocking)
            await self._run_security_tests(proxy_instance)

        except Exception as e:
            proxy_instance.is_working = False
            proxy_instance.security_issues.append(f"Connection failed: {str(e)}")
        finally:
            if self.session:
                await self.session.close()
                self.session = None
            if self.proxy:
                await self.proxy.stop()
                self.proxy = None

    async def _run_security_tests(self, proxy: Proxy):
        """Run security tests on proxy."""
        try:
            # Test 1: Redirect handling
            async with self.session.get(
                SECURITY_TESTS["redirect"],
                timeout=aiohttp.ClientTimeout(total=SECURITY_CHECK_TIMEOUT),
                allow_redirects=False
            ) as response:
                if response.status not in [301, 302, 307, 308]:
                    proxy.security_issues.append("Improper redirect handling")

            # Test 2: Header preservation
            async with self.session.get(
                SECURITY_TESTS["headers"],
                timeout=aiohttp.ClientTimeout(total=SECURITY_CHECK_TIMEOUT)
            ) as response:
                headers = await response.json()
                if "User-Agent" not in headers.get("headers", {}):
                    proxy.security_issues.append("Headers not preserved")

            # Test 3: Content injection check
            async with self.session.get(
                SECURITY_TESTS["content"],
                timeout=aiohttp.ClientTimeout(total=SECURITY_CHECK_TIMEOUT)
            ) as response:
                text = await response.text()
                if "eval(" in text or "atob(" in text or "<script>alert" in text.lower():
                    proxy.security_issues.append("Content injection detected")
                    proxy.is_secure = False

            # Test 4: SSL/TLS check
            try:
                async with self.session.get(
                    SECURITY_TESTS["ssl"],
                    timeout=aiohttp.ClientTimeout(total=SECURITY_CHECK_TIMEOUT)
                ) as response:
                    ssl_info = await response.json()
                    rating = ssl_info.get("rating", "")
                    if rating and rating != "Probably Okay":
                        proxy.security_issues.append(f"Weak SSL: {rating}")
            except Exception:
                pass  # SSL test is optional

        except Exception as e:
            proxy.security_issues.append(f"Security test error: {str(e)}")

        # Mark proxy as insecure if critical issues found
        if any("injection" in issue.lower() or "malicious" in issue.lower() for issue in proxy.security_issues):
            proxy.is_secure = False
            proxy.is_working = False


async def fetch_from_source(session: aiohttp.ClientSession, source: str) -> list[str]:
    """Fetch proxy configurations from a source."""
    try:
        async with session.get(source, timeout=aiohttp.ClientTimeout(total=30)) as response:
            response.raise_for_status()
            text = await response.text()
            return [
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
    except Exception as e:
        print(f"Error fetching {source}: {e}")
        return []


async def process_and_test_proxies(configs: list[str], progress: Progress) -> list[Proxy]:
    """Parse and test proxy configurations."""
    parsed = [Proxy.from_config(c) for c in configs]
    valid = [p for p in parsed if p is not None]

    if not valid:
        return []

    task = progress.add_task("[cyan]Testing proxies...", total=len(valid))
    results: list[Proxy] = []

    # Create workers
    num_workers = min(10, len(valid))
    workers = [SingBoxWorker() for _ in range(num_workers)]

    async def test_and_update(proxy: Proxy, worker: SingBoxWorker):
        tested = await Proxy.test(proxy, worker)
        results.append(tested)
        progress.update(task, advance=1)

    # Distribute work
    tasks = []
    for i, proxy in enumerate(valid):
        worker = workers[i % num_workers]
        tasks.append(test_and_update(proxy, worker))

    await asyncio.gather(*tasks, return_exceptions=True)

    # Sort by working status and latency
    working = sorted(
        [p for p in results if p.is_working and p.is_secure and p.latency is not None],
        key=lambda p: p.latency
    )
    non_working = [p for p in results if not p.is_working or not p.is_secure]

    return working + non_working


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
                "country": p.country,
                "country_code": p.country_code,
                "city": p.city,
                "asn": p.asn,
                "asn_number": p.asn_number,
                "remarks": p.remarks or f"{p.protocol}-{p.address}",
                "address": p.address,
                "port": p.port,
                "latency": p.latency,
                "is_secure": p.is_secure,
                "security_issues": p.security_issues,
                "tested_at": p.tested_at,
                "config": p.config,
            })

    return json.dumps(proxy_data, indent=2, ensure_ascii=False)


def generate_statistics_json(proxies: list[Proxy]) -> str:
    """Generate statistics JSON."""
    working = [p for p in proxies if p.is_working and p.is_secure]

    # Protocol distribution
    protocols = {}
    for p in working:
        protocols[p.protocol] = protocols.get(p.protocol, 0) + 1

    # Country distribution
    countries = {}
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
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }

    return json.dumps(stats, indent=2)