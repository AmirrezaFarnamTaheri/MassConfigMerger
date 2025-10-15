from __future__ import annotations

import asyncio
import base64
import json
import random
import socket
from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import parse_qs, unquote, urlparse

import aiohttp
import yaml
from aiohttp_proxy import ProxyConnector
from aiohttp_proxy.errors import SocksConnectionError
from rich.progress import Progress
import geoip2.database
from singbox2proxy import SingBoxProxy

# The URL to test proxies against.
# Using a URL that returns a 204 No Content response is efficient.
TEST_URL = "https://www.google.com/generate_204"

# Timeout for testing each proxy, in seconds.
TEST_TIMEOUT = 5


@dataclass
class Proxy:
    """Represents a parsed and testable proxy configuration."""

    config: str
    protocol: str = "unknown"
    is_working: bool = False
    latency: float | None = None  # in milliseconds
    country: str = "Unknown"
    asn: str = "Unknown"

    # Parsed fields
    remarks: str = ""
    address: str = ""
    port: int = 0
    uuid: str = ""
    security: str = "auto"
    # Add other protocol-specific fields as needed
    _details: dict = field(default_factory=dict)

    # A simple cache to avoid re-testing the same proxy config multiple times
    _test_cache: ClassVar[dict[str, "Proxy"]] = {}

    @classmethod
    def from_config(cls, config: str) -> "Proxy" | None:
        """
        Parses a raw proxy configuration string (e.g., vmess://, ss://)
        and returns a Proxy instance.
        """
        if config.startswith("vmess://"):
            return cls._parse_vmess(config)
        elif config.startswith("vless://"):
            return cls._parse_vless(config)
        elif config.startswith("ss://"):
            return cls._parse_ss(config)
        elif config.startswith("trojan://"):
            return cls._parse_trojan(config)
        elif any(config.startswith(f"{p}://") for p in ["hy2", "hysteria", "tuic", "wg", "ssh", "http", "https", "socks", "socks4", "socks5"]) or config.startswith("naive+https://"):
            return cls._parse_generic(config)
        return None

    @staticmethod
    def _parse_generic(config: str) -> "Proxy" | None:
        """Parses a generic URI format for protocols like hy2, hysteria, tuic, wg."""
        try:
            if config.startswith("naive+https://"):
                # urlparse doesn't handle custom schemes with '+' well, so we replace it temporarily
                parsed_url = urlparse(config.replace("naive+", "https"))
                protocol = "naive+https"
            else:
                parsed_url = urlparse(config)
                protocol = parsed_url.scheme
            query_params = parse_qs(parsed_url.query)

            return Proxy(
                config=config,
                protocol=protocol,
                remarks=unquote(parsed_url.fragment),
                address=parsed_url.hostname,
                port=parsed_url.port,
                uuid=parsed_url.username,
                _details={
                    key: value[0] for key, value in query_params.items()
                },
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_trojan(config: str) -> "Proxy" | None:
        """Parses a trojan:// URI."""
        try:
            parsed_url = urlparse(config)
            query_params = parse_qs(parsed_url.query)

            return Proxy(
                config=config,
                protocol="trojan",
                remarks=unquote(parsed_url.fragment),
                address=parsed_url.hostname,
                port=parsed_url.port,
                uuid=parsed_url.username,
                _details={
                    key: value[0] for key, value in query_params.items()
                },
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_ss(config: str) -> "Proxy" | None:
        """Parses a ss:// URI."""
        try:
            parsed_url = urlparse(config)

            # The format is ss://base64(method:password)@server:port#remarks
            encoded_user_info = parsed_url.username
            if not encoded_user_info:
                return None

            # Decode the user info from Base64, adding padding if necessary
            padded_encoded_info = encoded_user_info + '=' * (-len(encoded_user_info) % 4)
            decoded_user_info_bytes = base64.b64decode(padded_encoded_info)
            decoded_user_info = decoded_user_info_bytes.decode("utf-8")

            if ":" not in decoded_user_info:
                return None # Invalid format

            method, password = decoded_user_info.split(":", 1)

            return Proxy(
                config=config,
                protocol="ss",
                remarks=unquote(parsed_url.fragment),
                address=parsed_url.hostname,
                port=parsed_url.port,
                _details={"method": method, "password": password},
            )
        except (TypeError, ValueError, base64.binascii.Error):
            return None

    @staticmethod
    def _parse_vless(config: str) -> "Proxy" | None:
        """Parses a vless:// URI."""
        try:
            parsed_url = urlparse(config)
            query_params = parse_qs(parsed_url.query)

            return Proxy(
                config=config,
                protocol="vless",
                remarks=unquote(parsed_url.fragment),
                address=parsed_url.hostname,
                port=parsed_url.port,
                uuid=parsed_url.username,
                _details={
                    key: value[0] for key, value in query_params.items()
                },
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_vmess(config: str) -> "Proxy" | None:
        """Parses a vmess:// URI."""
        try:
            encoded_json = config[len("vmess://"):]
            # Add padding if required for correct Base64 decoding
            padded_encoded_json = encoded_json + '=' * (-len(encoded_json) % 4)
            decoded_json = base64.b64decode(padded_encoded_json).decode("utf-8")
            details = json.loads(decoded_json)

            return Proxy(
                config=config,
                protocol="vmess",
                remarks=details.get("ps", "N/A"),
                address=details.get("add", ""),
                port=int(details.get("port", 0)),
                uuid=details.get("id", ""),
                security=details.get("scy", "auto"),
                _details=details,
            )
        except (json.JSONDecodeError, base64.binascii.Error, TypeError, ValueError) as e:
            # Failed to parse, return None
            # print(f"Failed to parse VMess config: {e}") # Optional: for debugging
            return None

    @classmethod
    async def test(cls, proxy_instance: "Proxy", worker: "SingBoxWorker") -> "Proxy":
        """
        Tests a single proxy configuration to see if it's working and measures latency.
        Uses a simple cache to avoid re-testing.
        """
        if proxy_instance.config in cls._test_cache:
            return cls._test_cache[proxy_instance.config]

        if proxy_instance.protocol not in ["vmess", "vless", "ss", "trojan", "hy2", "hysteria", "tuic", "wg", "ssh", "http", "https", "socks", "socks4", "socks5", "naive+https"]:
            proxy_instance.is_working = False
            cls._test_cache[proxy_instance.config] = proxy_instance
            return proxy_instance

        try:
            with geoip2.database.Reader("data/GeoLite2-Country.mmdb") as reader:
                response = reader.country(proxy_instance.address)
                proxy_instance.country = response.country.iso_code
        except (geoip2.errors.AddressNotFoundError, FileNotFoundError):
            pass  # Keep country as "Unknown"

        try:
            with geoip2.database.Reader("data/ip-to-asn.mmdb") as reader:
                response = reader.asn(proxy_instance.address)
                proxy_instance.asn = f"AS{response.autonomous_system_number} ({response.autonomous_system_organization})"
        except (geoip2.errors.AddressNotFoundError, FileNotFoundError):
            pass

        try:
            await worker.test_proxy(proxy_instance)
        except Exception:
            proxy_instance.is_working = False

        cls._test_cache[proxy_instance.config] = proxy_instance
        return proxy_instance


class SingBoxWorker:
    """A worker that manages a long-lived sing-box process for testing proxies."""

    def __init__(self):
        self.proxy: SingBoxProxy | None = None

    async def test_proxy(self, proxy_instance: Proxy):
        """Tests a single proxy configuration."""
        self.proxy = SingBoxProxy(proxy_instance.config)
        await self.proxy.start()

        try:
            connector = ProxyConnector.from_url(self.proxy.http_proxy_url)
            async with aiohttp.ClientSession(connector=connector) as session:
                start_time = asyncio.get_event_loop().time()
                async with session.get(TEST_URL, timeout=TEST_TIMEOUT) as response:
                    if response.status == 204:
                        end_time = asyncio.get_event_loop().time()
                        proxy_instance.latency = (end_time - start_time) * 1000
                        proxy_instance.is_working = True
                    else:
                        proxy_instance.is_working = False
                        return

                # Security tests
                async with session.get("http://httpbin.org/redirect/1", timeout=TEST_TIMEOUT, allow_redirects=False) as response:
                    if response.status not in [301, 302, 307, 308]:
                        proxy_instance.is_working = False
                        return

                async with session.get("http://httpbin.org/headers", timeout=TEST_TIMEOUT) as response:
                    headers = await response.json()
                    if "User-Agent" not in headers["headers"] or "Accept-Encoding" not in headers["headers"]:
                        proxy_instance.is_working = False
                        return

                async with session.get("http://example.com", timeout=TEST_TIMEOUT) as response:
                    text = await response.text()
                    if "eval(" in text or "atob(" in text:
                        proxy_instance.is_working = False
                        return

                # Check for common open ports
                common_ports = [21, 22, 23, 25, 110]
                for port in common_ports:
                    try:
                        sock = socket.create_connection((proxy_instance.address, port), timeout=1)
                        sock.close()
                        # If the connection succeeds, the port is open
                        proxy_instance.is_working = False
                        return
                    except (socket.timeout, ConnectionRefusedError):
                        # The port is closed, which is good
                        pass
        finally:
            if self.proxy:
                await self.proxy.stop()
                self.proxy = None


async def fetch_from_source(session: aiohttp.ClientSession, source: str) -> list[str]:
    """Fetches proxy configurations from a single URL source."""
    try:
        async with session.get(source, timeout=10) as response:
            response.raise_for_status()
            text = await response.text()
            # Filter out empty or commented lines
            return [
                line
                for line in text.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"Error fetching {source}: {e}")
        return []


async def process_and_test_proxies(
    configs: list[str], progress: Progress
) -> list[Proxy]:
    """
    Parses and tests a list of proxy configurations concurrently.
    """
    # Step 1: Parse all raw configs into Proxy objects
    parsed_proxies = [Proxy.from_config(c) for c in configs]
    valid_proxies = [p for p in parsed_proxies if p is not None]

    if not valid_proxies:
        return []

    # Step 2: Create a pool of workers
    num_workers = min(10, len(valid_proxies))
    workers = [SingBoxWorker() for _ in range(num_workers)]

    # Step 3: Test all valid proxies
    task = progress.add_task("[cyan]Testing proxies...", total=len(valid_proxies))
    results: list[Proxy] = []

    async def _test_and_update(proxy: Proxy, worker: SingBoxWorker):
        tested_proxy = await Proxy.test(proxy, worker)
        results.append(tested_proxy)
        progress.update(task, advance=1)

    # Distribute proxies among workers
    tasks = []
    for i, proxy in enumerate(valid_proxies):
        worker = workers[i % num_workers]
        tasks.append(_test_and_update(proxy, worker))

    await asyncio.gather(*tasks)

    # Sort working proxies by latency (lower is better)
    working_proxies = sorted(
        [p for p in results if p.is_working and p.latency is not None],
        key=lambda p: p.latency,
    )
    non_working_proxies = [p for p in results if not p.is_working]

    return working_proxies + non_working_proxies


def generate_base64_subscription(proxies: list[Proxy]) -> str:
    """Generates a Base64-encoded subscription file content."""
    working_configs = [p.config for p in proxies if p.is_working]
    if not working_configs:
        return ""
    # Each config is individually Base64-encoded, then joined by newlines.
    # The final result is then Base64-encoded again.
    combined_configs = "\n".join(working_configs)
    return base64.b64encode(combined_configs.encode("utf-8")).decode("utf-8")


def generate_clash_config(proxies: list[Proxy]) -> str:
    """Generates a Clash-compatible YAML configuration file."""
    proxy_list = []
    for proxy in (p for p in proxies if p.is_working):
        clash_proxy = None
        if proxy.protocol == "vmess":
            clash_proxy = {
                "name": proxy.remarks,
                "type": "vmess",
                "server": proxy.address,
                "port": proxy.port,
                "uuid": proxy.uuid,
                "alterId": proxy._details.get("aid", 0),
                "cipher": proxy.security,
                "tls": proxy._details.get("tls", "none") != "none",
                "network": proxy._details.get("net", "tcp"),
            }
        elif proxy.protocol == "vless":
            clash_proxy = {
                "name": proxy.remarks,
                "type": "vless",
                "server": proxy.address,
                "port": proxy.port,
                "uuid": proxy.uuid,
                "tls": proxy._details.get("security", "none") == "tls",
                "network": proxy._details.get("type", "tcp"),
            }
        elif proxy.protocol == "ss":
            clash_proxy = {
                "name": proxy.remarks,
                "type": "ss",
                "server": proxy.address,
                "port": proxy.port,
                "cipher": proxy._details.get("method"),
                "password": proxy._details.get("password"),
            }
        elif proxy.protocol == "trojan":
            clash_proxy = {
                "name": proxy.remarks,
                "type": "trojan",
                "server": proxy.address,
                "port": proxy.port,
                "password": proxy.uuid,
                "tls": proxy._details.get("security", "none") == "tls",
                "network": proxy._details.get("type", "tcp"),
            }
        elif proxy.protocol == "hysteria":
            clash_proxy = {
                "name": proxy.remarks,
                "type": "hysteria",
                "server": proxy.address,
                "port": proxy.port,
                "auth_str": proxy.uuid,
                "up": proxy._details.get("up", 100),
                "down": proxy._details.get("down", 500),
            }
        elif proxy.protocol == "tuic":
            clash_proxy = {
                "name": proxy.remarks,
                "type": "tuic",
                "server": proxy.address,
                "port": proxy.port,
                "uuid": proxy.uuid,
                "password": proxy._details.get("password", ""),
            }
        elif proxy.protocol in ["http", "https"]:
            clash_proxy = {
                "name": proxy.remarks,
                "type": "http",
                "server": proxy.address,
                "port": proxy.port,
                "user": proxy.uuid,
                "password": proxy._details.get("password", ""),
                "tls": proxy.protocol == "https",
            }
        elif proxy.protocol in ["socks", "socks4", "socks5"]:
            clash_proxy = {
                "name": proxy.remarks,
                "type": "socks5",
                "server": proxy.address,
                "port": proxy.port,
                "user": proxy.uuid,
                "password": proxy._details.get("password", ""),
            }

        if clash_proxy:
            proxy_list.append(clash_proxy)

    if not proxy_list:
        return ""

    # Basic Clash config structure
    clash_config = {
        "proxies": proxy_list,
        "proxy-groups": [
            {
                "name": "ConfigStream-Proxies",
                "type": "select",
                "proxies": [p["name"] for p in proxy_list],
            }
        ],
        "rules": ["MATCH,ConfigStream-Proxies"],
    }

    # Use yaml.dump for proper formatting
    return yaml.dump(clash_config, sort_keys=False, indent=2)


def generate_raw_configs(proxies: list[Proxy]) -> str:
    """Generates a file with all working raw configuration links."""
    return "\n".join([p.config for p in proxies if p.is_working])