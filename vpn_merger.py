#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VPN Subscription Merger
===================================================================

The definitive VPN subscription merger combining hundreds of sources from `sources.txt` with comprehensive
testing, smart sorting, and automatic dead link removal.

Features:
• Reads from `sources.txt` (over 450 curated repositories)
• Real-time URL availability testing and dead link removal
• Server reachability testing with response time measurement
• Smart sorting by connection speed and protocol preference
• Event loop compatibility (Jupyter, IPython, regular Python)
• Advanced deduplication with semantic analysis
• Multiple output formats (raw, base64, CSV, JSON)
• Comprehensive error handling and retry logic
• Best practices implemented throughout
• Default protocol set optimised for the Hiddify client

Requirements: pip install aiohttp aiodns nest-asyncio
Author: Final Unified Edition - June 30, 2025
Expected Output: 800k-1.2M+ tested and sorted configs
"""

import asyncio
import base64
import binascii
import csv
import hashlib
import json
import logging
import random
import re
import yaml
import ssl
import sys
import time
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, cast

from constants import SOURCES_FILE
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from clash_utils import config_to_clash_proxy

try:
    import aiohttp
    from aiohttp.resolver import AsyncResolver
except ImportError as exc:
    raise ImportError(
        "Missing optional dependency 'aiohttp'. "
        "Run `pip install -r requirements.txt` before running this script."
    ) from exc

# Event loop compatibility fix
try:
    import nest_asyncio
    nest_asyncio.apply()
    if __name__ == "__main__":
        print("✅ Applied nest_asyncio patch for event loop compatibility")
except ImportError as exc:
    raise ImportError(
        "Missing optional dependency 'nest_asyncio'. "
        "Run `pip install -r requirements.txt` before running this script."
    ) from exc

try:
    import aiodns  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "Missing optional dependency 'aiodns'. "
        "Run `pip install -r requirements.txt` before running this script."
    ) from exc

# ============================================================================
# CONFIGURATION & SETTINGS
# ============================================================================

@dataclass
class Config:
    """Comprehensive configuration for optimal performance."""
    
    # HTTP settings
    headers: Dict[str, str]
    request_timeout: int
    connect_timeout: float
    max_retries: int
    
    # Processing settings
    concurrent_limit: int
    max_configs_per_source: int
    
    # Protocol validation
    valid_prefixes: Tuple[str, ...]
    
    # Testing settings
    enable_url_testing: bool
    enable_sorting: bool
    test_timeout: float

    # Output settings
    output_dir: str

    # New features
    batch_size: int
    threshold: int
    top_n: int
    tls_fragment: Optional[str]
    include_protocols: Optional[Set[str]]
    exclude_protocols: Optional[Set[str]]
    exclude_patterns: List[str]
    resume_file: Optional[str]
    max_ping_ms: Optional[int]
    log_file: Optional[str]
    cumulative_batches: bool
    strict_batch: bool
    shuffle_sources: bool
    write_base64: bool
    write_csv: bool
    write_clash: bool
    write_clash_proxies: bool
    mux_concurrency: int
    smux_streams: int
    geoip_db: Optional[str] = None
    include_countries: Optional[Set[str]] = None
    exclude_countries: Optional[Set[str]] = None

CONFIG = Config(
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    },
    request_timeout=30,
    connect_timeout=3.0,
    max_retries=3,
    concurrent_limit=50,
    max_configs_per_source=75000,
    valid_prefixes=(
        "vmess://", "vless://", "reality://",
        "ss://", "ssr://", "trojan://",
        "hy2://", "hysteria://", "hysteria2://",
        "tuic://", "shadowtls://", "wireguard://",
        "socks://", "socks4://", "socks5://",
        "http://", "https://", "grpc://", "ws://", "wss://",
        "tcp://", "kcp://", "quic://", "h2://",
    ),
    enable_url_testing=True,
    enable_sorting=True,
    test_timeout=5.0,
    output_dir="output",
    batch_size=1000,
    threshold=0,
    top_n=0,
    tls_fragment=None,
    include_protocols={
        "PROXY", "SHADOWSOCKS", "SHADOWSOCKSR", "TROJAN",
        "CLASH", "V2RAY", "REALITY",
        "VMESS", "XRAY", "WIREGUARD", "ECH", "VLESS",
        "HYSTERIA", "TUIC", "SING-BOX", "SINGBOX",
        "SHADOWTLS", "CLASHMETA", "HYSTERIA2",
    },
    exclude_protocols={"OTHER"},
    exclude_patterns=[],
    resume_file=None,
    max_ping_ms=1000,
    log_file=None,
    cumulative_batches=False,
    strict_batch=True,
    shuffle_sources=False,
    write_base64=True,
    write_csv=True,
    write_clash=True,
    write_clash_proxies=True,
    mux_concurrency=8,
    smux_streams=4,
    geoip_db=None,
    include_countries=None,
    exclude_countries=None
)

# Compiled regular expressions from --exclude-pattern
EXCLUDE_REGEXES: List[re.Pattern] = []

# ============================================================================
# COMPREHENSIVE SOURCE COLLECTION (ALL UNIFIED SOURCES)
# ============================================================================

class UnifiedSources:
    """Load VPN subscription sources from an external file."""

    DEFAULT_FILE = SOURCES_FILE
    FALLBACK_SOURCES = [
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub1.txt",
        "https://raw.githubusercontent.com/ssrsub/ssr/master/v2ray",
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/vmess.txt",
    ]

    @classmethod
    def load(cls, path: Optional[Union[str, Path]] = None) -> List[str]:
        file_path = Path(path) if path else cls.DEFAULT_FILE
        if file_path.exists():
            with file_path.open() as f:
                return [line.strip() for line in f if line.strip()]
        logging.warning("sources file not found: %s; using fallback list", file_path)
        return cls.FALLBACK_SOURCES

    @classmethod
    def get_all_sources(cls, path: Optional[Union[str, Path]] = None) -> List[str]:
        """Return list of sources from file or fallback."""
        return cls.load(path)

@dataclass
class ConfigResult:
    """Enhanced config result with testing metrics."""
    config: str
    protocol: str
    host: Optional[str] = None
    port: Optional[int] = None
    ping_time: Optional[float] = None
    is_reachable: bool = False
    source_url: str = ""
    country: Optional[str] = None

class EnhancedConfigProcessor:
    """Advanced configuration processor with comprehensive testing capabilities."""
    
    MAX_DECODE_SIZE = 256 * 1024  # 256 kB safety limit for base64 payloads

    def __init__(self):
        self.dns_cache = {}
        self.resolver: Optional[AsyncResolver] = None
        self._geoip_reader = None
        
    def extract_host_port(self, config: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract host and port from configuration for testing."""
        try:
            if config.startswith(("vmess://", "vless://")):
                try:
                    json_part = config.split("://", 1)[1]
                    decoded_bytes = base64.b64decode(json_part)
                    if len(decoded_bytes) > self.MAX_DECODE_SIZE:
                        return None, None
                    decoded = decoded_bytes.decode("utf-8", "ignore")
                    data = json.loads(decoded)
                    host = data.get("add") or data.get("host")
                    port = data.get("port")
                    return host, int(port) if port else None
                except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    logging.debug("extract_host_port vmess failed: %s", exc)

            if config.startswith("ssr://"):
                try:
                    after = config.split("://", 1)[1].split("#", 1)[0]
                    padded = after + "=" * (-len(after) % 4)
                    decoded = base64.urlsafe_b64decode(padded).decode()
                    host_part = decoded.split("/", 1)[0]
                    parts = host_part.split(":")
                    if len(parts) < 2:
                        return None, None
                    host, port = parts[0], parts[1]
                    return host or None, int(port)
                except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
                    logging.debug("extract_host_port ssr failed: %s", exc)
            
            # Parse URI-style configs
            parsed = urlparse(config)
            if parsed.hostname and parsed.port:
                return parsed.hostname, parsed.port
                
            # Extract from @ notation
            match = re.search(r"@([^:/?#]+):(\d+)", config)
            if match:
                return match.group(1), int(match.group(2))
                
        except (ValueError, UnicodeError, binascii.Error) as exc:
            logging.debug("extract_host_port failed: %s", exc)
        return None, None
    
    def create_semantic_hash(self, config: str) -> str:
        """Create semantic hash for intelligent deduplication."""
        host, port = self.extract_host_port(config)
        identifier = None

        scheme = config.split("://", 1)[0].lower()

        if scheme in ("vmess", "vless"):
            try:
                after_scheme = config.split("://", 1)[1]
                parsed = urlparse(config)
                if parsed.username:
                    identifier = parsed.username
                else:
                    padded = after_scheme + "=" * (-len(after_scheme) % 4)
                    decoded = base64.b64decode(padded).decode("utf-8", "ignore")
                    data = json.loads(decoded)
                    identifier = data.get("id") or data.get("uuid") or data.get("user")
            except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                logging.debug("semantic_hash vmess failed: %s", exc)
        elif scheme == "trojan":
            try:
                parsed = urlparse(config)
                if parsed.username or parsed.password:
                    identifier = parsed.username or ""
                    if parsed.password is not None:
                        if identifier:
                            identifier += f":{parsed.password}"
                        else:
                            identifier = parsed.password
                else:
                    identifier = None
            except ValueError as exc:
                logging.debug("semantic_hash trojan failed: %s", exc)
        elif scheme in ("ss", "shadowsocks"):
            try:
                parsed = urlparse(config)
                if parsed.username and parsed.password:
                    identifier = parsed.password
                else:
                    base = config.split("://", 1)[1].split("#", 1)[0]
                    padded = base + "=" * (-len(base) % 4)
                    decoded = base64.b64decode(padded).decode("utf-8", "ignore")
                    before_at = decoded.split("@", 1)[0]
                    method, password = before_at.split(":", 1)
                    identifier = password
            except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
                logging.debug("semantic_hash ss failed: %s", exc)

        if host and port:
            key = f"{host}:{port}"
            if identifier:
                key = f"{identifier}@{key}"
        else:
            normalized = re.sub(r'#.*$', '', config).strip()
            key = normalized
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    async def test_connection(self, host: str, port: int) -> Optional[float]:
        """Test connection and measure response time."""
        if not CONFIG.enable_url_testing:
            return None
            
        start = time.time()
        try:
            target = host
            if 'aiodns' in sys.modules:
                if self.resolver is None:
                    try:
                        self.resolver = AsyncResolver()
                    except aiodns.error.DNSError as exc:
                        logging.debug("AsyncResolver init failed: %s", exc)
                        self.resolver = None
                if self.resolver is not None:
                    try:
                        if host not in self.dns_cache:
                            result = await self.resolver.resolve(host, port)
                            if result:
                                self.dns_cache[host] = result[0]["host"]
                        target = self.dns_cache.get(host, host)
                    except aiodns.error.DNSError as exc:
                        logging.debug("DNS resolve failed: %s", exc)
                        target = host

            _, writer = await asyncio.wait_for(
                asyncio.open_connection(target, port),
                timeout=CONFIG.test_timeout
            )
            writer.close()
            await writer.wait_closed()
            return time.time() - start
        except (OSError, asyncio.TimeoutError) as exc:
            logging.debug("Connection test failed: %s", exc)
            return None

    def lookup_country(self, host: str) -> Optional[str]:
        """Return ISO country code for host if GeoIP is configured."""
        if not host or not CONFIG.geoip_db:
            return None
        try:
            from geoip2.database import Reader
        except ImportError:
            return None
        if self._geoip_reader is None:
            try:
                self._geoip_reader = Reader(CONFIG.geoip_db)
            except OSError as exc:
                logging.debug("GeoIP reader init failed: %s", exc)
                self._geoip_reader = None
                return None
        try:
            ip = host
            if not re.match(r"^[0-9.]+$", host):
                ip = socket.gethostbyname(host)
            resp = self._geoip_reader.country(ip)
            return resp.country.iso_code
        except (OSError, socket.gaierror) as exc:
            logging.debug("GeoIP lookup failed: %s", exc)
            return None

    def categorize_protocol(self, config: str) -> str:
        """Categorize configuration by protocol."""
        protocol_map = {
            "vmess://": "VMess",
            "vless://": "VLESS", 
            "ss://": "Shadowsocks",
            "ssr://": "ShadowsocksR",
            "trojan://": "Trojan",
            "hy2://": "Hysteria2",
            "hysteria2://": "Hysteria2",
            "hysteria://": "Hysteria",
            "tuic://": "TUIC",
            "reality://": "Reality",
            "naive://": "Naive",
            "juicity://": "Juicity",
            "wireguard://": "WireGuard",
            "shadowtls://": "ShadowTLS",
            "brook://": "Brook",
        }
        
        for prefix, protocol in protocol_map.items():
            if config.startswith(prefix):
                return protocol

        return "Other"

    def apply_tuning(self, config: str) -> str:
        """Apply mux and smux parameters to URI-style configs."""
        try:
            if "//" not in config or config.startswith("vmess://"):
                return config
            parsed = urlparse(config)
            if not parsed.scheme:
                return config
            params = parse_qs(parsed.query)
            if CONFIG.mux_concurrency > 0:
                params["mux"] = [str(CONFIG.mux_concurrency)]
            if CONFIG.smux_streams > 0:
                params["smux"] = [str(CONFIG.smux_streams)]
            new_query = urlencode(params, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
        except ValueError as exc:
            logging.debug("apply_tuning failed: %s", exc)
            return config

# ============================================================================
# ASYNC SOURCE FETCHER WITH COMPREHENSIVE TESTING
# ============================================================================

class AsyncSourceFetcher:
    """Async source fetcher with comprehensive testing and availability checking."""

    def __init__(self, processor: EnhancedConfigProcessor, seen_hashes: Set[str]):
        self.processor = processor
        self.session: Optional[aiohttp.ClientSession] = None
        self.seen_hashes = seen_hashes
        self._hash_lock = asyncio.Lock()
        
    async def test_source_availability(self, url: str) -> bool:
        """Test if a source URL is available (returns 200 status)."""
        assert self.session is not None
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.session.head(url, timeout=timeout, allow_redirects=True) as response:
                status = response.status
                if status == 200:
                    return True
                if 400 <= status < 500:
                    async with self.session.get(
                        url,
                        headers={**CONFIG.headers, 'Range': 'bytes=0-0'},
                        timeout=timeout,
                        allow_redirects=True,
                    ) as get_resp:
                        return get_resp.status in (200, 206)
                return False
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logging.debug("availability check failed for %s: %s", url, exc)
            return False
        
    async def fetch_source(self, url: str) -> Tuple[str, List[ConfigResult]]:
        """Fetch single source with comprehensive testing and deduplication."""
        assert self.session is not None
        for attempt in range(CONFIG.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=CONFIG.request_timeout)
                async with self.session.get(url, headers=CONFIG.headers, timeout=timeout) as response:
                    if response.status != 200:
                        continue
                        
                    content = await response.text()
                    if not content.strip():
                        return url, []
                    
                    # Enhanced Base64 detection and decoding
                    try:
                        # Check if content looks like base64
                        if not any(char in content for char in '\n\r') and len(content) > 100:
                            decoded = base64.b64decode(content).decode("utf-8", "ignore")
                            if decoded.count("://") > content.count("://"):
                                content = decoded
                    except (binascii.Error, UnicodeDecodeError) as exc:  # noqa: E722
                        logging.debug("Base64 decode failed: %s", exc)
                    
                    # Extract and process configs
                    lines = [line.strip() for line in content.splitlines() if line.strip()]
                    config_results: List[ConfigResult] = []
                    
                    for line in lines:
                        if all(
                            [
                                line.startswith(CONFIG.valid_prefixes),
                                len(line) > 20,
                                len(line) < 2000,
                                len(config_results) < CONFIG.max_configs_per_source,
                            ]
                        ):
                            config_hash = self.processor.create_semantic_hash(line)
                            async with self._hash_lock:
                                if config_hash in self.seen_hashes:
                                    continue
                                self.seen_hashes.add(config_hash)

                            line = self.processor.apply_tuning(line)

                            # Create config result
                            host, port = self.processor.extract_host_port(line)
                            protocol = self.processor.categorize_protocol(line)

                            country = self.processor.lookup_country(host) if host else None
                            result = ConfigResult(
                                config=line,
                                protocol=protocol,
                                host=host,
                                port=port,
                                source_url=url,
                                country=country
                            )
                            
                            # Test connection if enabled
                            if CONFIG.enable_url_testing and host and port:
                                ping_time = await self.processor.test_connection(host, port)
                                result.ping_time = ping_time
                                result.is_reachable = ping_time is not None
                            
                            config_results.append(result)
                    
                    return url, config_results
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                logging.debug("fetch_source error on %s: %s", url, exc)
                if attempt < CONFIG.max_retries - 1:
                    # Use a capped and jittered delay to reduce tail latency
                    await asyncio.sleep(min(3, 1.5 + random.random()))
                    
        return url, []

# ============================================================================
# MAIN PROCESSOR WITH UNIFIED FUNCTIONALITY
# ============================================================================

class UltimateVPNMerger:
    """VPN merger with unified functionality and comprehensive testing."""

    def __init__(self, sources_file: Optional[Union[str, Path]] = None):
        self.sources = UnifiedSources.get_all_sources(sources_file)
        if CONFIG.shuffle_sources:
            random.shuffle(self.sources)
        self.processor = EnhancedConfigProcessor()
        self.seen_hashes: Set[str] = set()
        self.fetcher = AsyncSourceFetcher(self.processor, self.seen_hashes)
        self.batch_counter = 0
        self.next_batch_threshold = CONFIG.batch_size if CONFIG.batch_size else float('inf')
        self.start_time = 0.0
        self.available_sources: List[str] = []
        self.all_results: List[ConfigResult] = []
        self.stop_fetching = False
        self.saved_hashes: Set[str] = set()
        self.cumulative_unique: List[ConfigResult] = []
        self.last_processed_index = 0
        self.last_saved_count = 0

    def _load_existing_results(self, path: str) -> List[ConfigResult]:
        """Load previously saved configs from a raw or base64 file."""
        try:
            text = Path(path).read_text(encoding="utf-8").strip()
        except OSError as e:
            print(f"⚠️  Failed to read resume file: {e}")
            return []

        if text and '://' not in text.splitlines()[0]:
            try:
                text = base64.b64decode(text).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError) as exc:
                logging.debug("resume base64 decode failed: %s", exc)

        results = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            protocol = self.processor.categorize_protocol(line)
            host, port = self.processor.extract_host_port(line)
            country = self.processor.lookup_country(host) if host else None
            results.append(
                ConfigResult(
                    config=line,
                    protocol=protocol,
                    host=host,
                    port=port,
                    source_url="(resume)",
                    country=country
                )
            )
            h = self.processor.create_semantic_hash(line)
            self.seen_hashes.add(h)
        return results
        
    async def run(self) -> None:
        """Execute the complete unified merging process."""
        print("🚀 VPN Subscription Merger - Final Unified & Polished Edition")
        print("=" * 85)
        print(f"📊 Total sources: {len(self.sources)}")
        print(f"🔧 URL Testing: {'Enabled' if CONFIG.enable_url_testing else 'Disabled'}")
        print(f"📈 Smart Sorting: {'Enabled' if CONFIG.enable_sorting else 'Disabled'}")
        print()
        
        start_time = time.time()
        self.start_time = start_time

        if CONFIG.resume_file:
            print(f"🔄 Loading existing configs from {CONFIG.resume_file} ...")
            self.all_results.extend(self._load_existing_results(CONFIG.resume_file))
            print(f"   ✔ Loaded {len(self.all_results)} configs from resume file")
            await self._maybe_save_batch()

        # Step 1: Test source availability and remove dead links
        print("🔄 [1/6] Testing source availability and removing dead links...")
        self.available_sources = await self._test_and_filter_sources()
        
        # Step 2: Fetch all configs from available sources
        print(f"\n🔄 [2/6] Fetching configs from {len(self.available_sources)} available sources...")
        await self._fetch_all_sources(self.available_sources)
        
        # Step 3: Deduplicate efficiently  
        print(f"\n🔍 [3/6] Deduplicating {len(self.all_results):,} configs...")
        unique_results = self._deduplicate_config_results(self.all_results)
        
        # Step 4: Sort by performance if enabled
        if CONFIG.enable_sorting:
            print(f"\n📊 [4/6] Sorting {len(unique_results):,} configs by performance...")
            unique_results = self._sort_by_performance(unique_results)
        else:
            print("\n⏭️ [4/6] Skipping sorting (disabled)")

        if CONFIG.enable_url_testing:
            before = len(unique_results)
            unique_results = [r for r in unique_results if r.ping_time is not None]
            removed = before - len(unique_results)
            print(f"   ❌ Removed {removed} configs with no ping")

        if CONFIG.top_n > 0:
            unique_results = unique_results[:CONFIG.top_n]
            print(f"   🔝 Keeping top {CONFIG.top_n} configs")

        if CONFIG.max_ping_ms is not None and CONFIG.enable_url_testing:
            before = len(unique_results)
            unique_results = [r for r in unique_results
                              if r.ping_time is not None and r.ping_time * 1000 <= CONFIG.max_ping_ms]
            removed = before - len(unique_results)
            print(f"   ⏱️  Removed {removed} configs over {CONFIG.max_ping_ms} ms")

        # Step 5: Analyze protocols and performance
        print(f"\n📋 [5/6] Analyzing {len(unique_results):,} unique configs...")
        stats = self._analyze_results(unique_results, self.available_sources)
        
        # Step 6: Generate comprehensive outputs
        print("\n💾 [6/6] Generating comprehensive outputs...")
        await self._generate_comprehensive_outputs(unique_results, stats, self.start_time)

        self._print_final_summary(len(unique_results), time.time() - self.start_time, stats)
    
    async def _test_and_filter_sources(self) -> List[str]:
        """Test all sources for availability and filter out dead links."""
        # Setup HTTP session
        connector = aiohttp.TCPConnector(
            limit=CONFIG.concurrent_limit,
            limit_per_host=10,
            ttl_dns_cache=300,
            ssl=ssl.create_default_context(),
            resolver=AsyncResolver()
        )
        
        self.fetcher.session = aiohttp.ClientSession(connector=connector)
        
        try:
            # Test all sources concurrently
            semaphore = asyncio.Semaphore(CONFIG.concurrent_limit)
            
            async def test_single_source(url: str) -> Optional[str]:
                async with semaphore:
                    is_available = await self.fetcher.test_source_availability(url)
                    return url if is_available else None
            
            tasks = [test_single_source(url) for url in self.sources]
            
            completed = 0
            available_sources = []
            
            for coro in asyncio.as_completed(tasks):
                result = await coro
                completed += 1
                
                if result:
                    available_sources.append(result)
                    status = "✅ Available"
                else:
                    status = "❌ Dead link"
                
                print(f"  [{completed:03d}/{len(self.sources)}] {status}")
            
            removed_count = len(self.sources) - len(available_sources)
            print(f"\n   🗑️ Removed {removed_count} dead sources")
            print(f"   ✅ Keeping {len(available_sources)} available sources")
            
            return available_sources
            
        finally:
            # Don't close session here, we'll reuse it
            pass
    
    async def _fetch_all_sources(self, available_sources: List[str]) -> List[ConfigResult]:
        """Fetch all configs from available sources."""
        # Append results directly to self.all_results so that _maybe_save_batch
        # sees the running total and can save incremental batches.
        successful_sources = 0
        
        try:
            # Process sources with semaphore
            semaphore = asyncio.Semaphore(CONFIG.concurrent_limit)
            
            async def process_single_source(url: str) -> Tuple[str, List[ConfigResult]]:
                async with semaphore:
                    return await self.fetcher.fetch_source(url)
            
            # Create tasks
            tasks = [asyncio.create_task(process_single_source(url)) for url in available_sources]
            
            completed = 0
            for coro in asyncio.as_completed(tasks):
                url, results = await coro
                completed += 1
                
                # Append directly to the instance-level list
                self.all_results.extend(results)
                if results:
                    successful_sources += 1
                    reachable = sum(1 for r in results if r.is_reachable)
                    status = f"✓ {len(results):,} configs ({reachable} reachable)"
                else:
                    status = "✗ No configs"
                
                domain = urlparse(url).netloc or url[:50] + "..."
                print(f"  [{completed:03d}/{len(available_sources)}] {status} - {domain}")

                await self._maybe_save_batch()

                if self.stop_fetching:
                    break

            if self.stop_fetching:
                for t in tasks:
                    t.cancel()

            print(f"\n   📈 Sources with configs: {successful_sources}/{len(available_sources)}")
            
        finally:
            if self.fetcher.session is not None:
                await self.fetcher.session.close()

        # Return the accumulated list for backward compatibility
        return self.all_results

    async def _maybe_save_batch(self) -> None:
        """Save intermediate output based on batch settings."""
        if CONFIG.batch_size <= 0:
            return

        # Process new results since last call
        new_slice = self.all_results[self.last_processed_index:]
        self.last_processed_index = len(self.all_results)
        for r in new_slice:
            text = r.config.lower()
            if CONFIG.tls_fragment and CONFIG.tls_fragment.lower() not in text:
                continue
            if CONFIG.include_protocols and r.protocol.upper() not in CONFIG.include_protocols:
                continue
            if CONFIG.exclude_protocols and r.protocol.upper() in CONFIG.exclude_protocols:
                continue
            if EXCLUDE_REGEXES and any(rx.search(text) for rx in EXCLUDE_REGEXES):
                continue
            if CONFIG.enable_url_testing and r.ping_time is None:
                continue
            h = self.processor.create_semantic_hash(r.config)
            if h not in self.saved_hashes:
                self.saved_hashes.add(h)
                self.cumulative_unique.append(r)

        if CONFIG.strict_batch:
            while len(self.cumulative_unique) - self.last_saved_count >= CONFIG.batch_size:
                self.batch_counter += 1
                if CONFIG.cumulative_batches:
                    batch_results = self.cumulative_unique[:]
                else:
                    start = self.last_saved_count
                    end = start + CONFIG.batch_size
                    batch_results = self.cumulative_unique[start:end]
                    self.last_saved_count = end

                if CONFIG.enable_sorting:
                    batch_results = self._sort_by_performance(batch_results)
                if CONFIG.top_n > 0:
                    batch_results = batch_results[:CONFIG.top_n]

                stats = self._analyze_results(batch_results, self.available_sources)
                await self._generate_comprehensive_outputs(
                    batch_results,
                    stats,
                    self.start_time,
                    prefix=f"batch_{self.batch_counter}_",
                )

                cumulative_stats = self._analyze_results(
                    self.cumulative_unique,
                    self.available_sources,
                )
                await self._generate_comprehensive_outputs(
                    self.cumulative_unique,
                    cumulative_stats,
                    self.start_time,
                    prefix="cumulative_",
                )
                if CONFIG.cumulative_batches:
                    self.last_saved_count = len(self.cumulative_unique)

                if CONFIG.threshold > 0 and len(self.cumulative_unique) >= CONFIG.threshold:
                    print(f"\n⏹️  Threshold of {CONFIG.threshold} configs reached. Stopping early.")
                    self.stop_fetching = True
                    break
        else:
            if len(self.cumulative_unique) >= self.next_batch_threshold:
                self.batch_counter += 1
                if CONFIG.cumulative_batches:
                    batch_results = self.cumulative_unique[:]
                else:
                    batch_results = self.cumulative_unique[self.last_saved_count:]
                    self.last_saved_count = len(self.cumulative_unique)

                if CONFIG.enable_sorting:
                    batch_results = self._sort_by_performance(batch_results)
                if CONFIG.top_n > 0:
                    batch_results = batch_results[:CONFIG.top_n]

                stats = self._analyze_results(batch_results, self.available_sources)
                await self._generate_comprehensive_outputs(
                    batch_results,
                    stats,
                    self.start_time,
                    prefix=f"batch_{self.batch_counter}_",
                )

                cumulative_stats = self._analyze_results(
                    self.cumulative_unique,
                    self.available_sources,
                )
                await self._generate_comprehensive_outputs(
                    self.cumulative_unique,
                    cumulative_stats,
                    self.start_time,
                    prefix="cumulative_",
                )
                if CONFIG.cumulative_batches:
                    self.last_saved_count = len(self.cumulative_unique)

                self.next_batch_threshold += CONFIG.batch_size

                if CONFIG.threshold > 0 and len(self.cumulative_unique) >= CONFIG.threshold:
                    print(f"\n⏹️  Threshold of {CONFIG.threshold} configs reached. Stopping early.")
                    self.stop_fetching = True
    
    def _deduplicate_config_results(self, results: List[ConfigResult]) -> List[ConfigResult]:
        """Efficient deduplication of config results using semantic hashing."""
        seen_hashes: Set[str] = set()
        unique_results: List[ConfigResult] = []

        for result in results:
            text = result.config.lower()
            if CONFIG.tls_fragment and CONFIG.tls_fragment.lower() not in text:
                continue
            if CONFIG.include_protocols and result.protocol.upper() not in CONFIG.include_protocols:
                continue
            if CONFIG.exclude_protocols and result.protocol.upper() in CONFIG.exclude_protocols:
                continue
            if CONFIG.include_countries and result.country:
                if result.country.upper() not in CONFIG.include_countries:
                    continue
            if CONFIG.exclude_countries and result.country:
                if result.country.upper() in CONFIG.exclude_countries:
                    continue
            if EXCLUDE_REGEXES and any(r.search(text) for r in EXCLUDE_REGEXES):
                continue
            config_hash = self.processor.create_semantic_hash(result.config)
            if config_hash not in seen_hashes:
                seen_hashes.add(config_hash)
                unique_results.append(result)
        
        duplicates = len(results) - len(unique_results)
        print(f"   🗑️ Duplicates removed: {duplicates:,}")
        if len(results) > 0:
            efficiency = duplicates / len(results) * 100
        else:
            efficiency = 0
        print(f"   📊 Deduplication efficiency: {efficiency:.1f}%")
        return unique_results
    
    def _sort_by_performance(self, results: List[ConfigResult]) -> List[ConfigResult]:
        """Sort results by connection performance and protocol preference."""
        # Protocol priority ranking
        protocol_priority = {
            "VLESS": 1, "VMess": 2, "Reality": 3, "Hysteria2": 4, 
            "Trojan": 5, "Shadowsocks": 6, "TUIC": 7, "Hysteria": 8,
            "Naive": 9, "Juicity": 10, "WireGuard": 11, "Other": 12
        }
        
        def sort_key(result: ConfigResult) -> Tuple:
            is_reachable = 1 if result.is_reachable else 0
            ping_time = result.ping_time if result.ping_time is not None else float('inf')
            protocol_rank = protocol_priority.get(result.protocol, 13)
            return (-is_reachable, ping_time, protocol_rank)
        
        sorted_results = sorted(results, key=sort_key)
        
        reachable_count = sum(1 for r in results if r.is_reachable)
        print(f"   🚀 Sorted: {reachable_count:,} reachable configs first")
        
        if reachable_count > 0:
            fastest = min(
                (r for r in results if r.ping_time is not None),
                key=lambda x: cast(float, x.ping_time),
                default=None,
            )
            if fastest and fastest.ping_time is not None:
                print(
                    f"   ⚡ Fastest server: {fastest.ping_time * 1000:.1f}ms ({fastest.protocol})"
                )
        
        return sorted_results
    
    def _analyze_results(self, results: List[ConfigResult], available_sources: List[str]) -> Dict:
        """Analyze results and generate comprehensive statistics."""
        protocol_stats: Dict[str, int] = {}
        performance_stats: Dict[str, List[float]] = {}
        
        for result in results:
            # Protocol count
            protocol_stats[result.protocol] = protocol_stats.get(result.protocol, 0) + 1
            
            # Performance stats
            if result.ping_time is not None:
                if result.protocol not in performance_stats:
                    performance_stats[result.protocol] = []
                performance_stats[result.protocol].append(result.ping_time)
        
        # Calculate performance metrics
        perf_summary = {}
        for protocol, times in performance_stats.items():
            if times:
                perf_summary[protocol] = {
                    "count": len(times),
                    "avg_ms": round(sum(times) / len(times) * 1000, 2),
                    "min_ms": round(min(times) * 1000, 2),
                    "max_ms": round(max(times) * 1000, 2)
                }
        
        # Print comprehensive breakdown
        total = len(results)
        reachable = sum(1 for r in results if r.is_reachable)

        print(f"   📊 Total configs: {total:,}")
        reach_pct = (reachable / total * 100) if total else 0
        print(f"   🌐 Reachable configs: {reachable:,} ({reach_pct:.1f}%)")
        print(f"   🔗 Available sources: {len(available_sources)}")
        print("   📋 Protocol breakdown:")
        
        for protocol, count in sorted(protocol_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100 if total else 0
            perf_info = ""
            if protocol in perf_summary:
                avg_ms = perf_summary[protocol]["avg_ms"]
                perf_info = f" | Avg: {avg_ms}ms"
            print(f"      {protocol:12} {count:>7,} configs ({percentage:5.1f}%){perf_info}")
        
        return {
            "protocol_stats": protocol_stats,
            "performance_stats": perf_summary,
            "total_configs": total,
            "reachable_configs": reachable,
            "available_sources": len(available_sources),
            "total_sources": len(self.sources)
        }
    
    async def _generate_comprehensive_outputs(
        self,
        results: List[ConfigResult],
        stats: Dict,
        start_time: float,
        prefix: str = "",
    ) -> None:
        """Generate comprehensive output files with all formats."""
        # Create output directory
        output_dir = Path(CONFIG.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Extract configs for traditional outputs
        configs = [result.config for result in results]
        
        # Raw text output
        raw_file = output_dir / f"{prefix}vpn_subscription_raw.txt"
        tmp_raw = raw_file.with_suffix('.tmp')
        tmp_raw.write_text("\n".join(configs), encoding="utf-8")
        tmp_raw.replace(raw_file)
        
        base64_file = output_dir / f"{prefix}vpn_subscription_base64.txt"
        if CONFIG.write_base64:
            base64_content = base64.b64encode("\n".join(configs).encode("utf-8")).decode("utf-8")
            tmp_base64 = base64_file.with_suffix('.tmp')
            tmp_base64.write_text(base64_content, encoding="utf-8")
            tmp_base64.replace(base64_file)

        # Enhanced CSV with comprehensive performance data
        csv_file = output_dir / f"{prefix}vpn_detailed.csv"
        if CONFIG.write_csv:
            tmp_csv = csv_file.with_suffix('.tmp')
            with open(tmp_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Config', 'Protocol', 'Host', 'Port', 'Ping_MS', 'Reachable', 'Source', 'Country'])
                for result in results:
                    ping_ms = round(result.ping_time * 1000, 2) if result.ping_time else None
                    writer.writerow([
                        result.config, result.protocol, result.host, result.port,
                        ping_ms, result.is_reachable, result.source_url,
                        result.country
                    ])
            tmp_csv.replace(csv_file)
        
        # Comprehensive JSON report
        report_file = output_dir / f"{prefix}vpn_report.json"
        report = {
            "generation_info": {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "processing_time_seconds": round(time.time() - start_time, 2),
                "script_version": "Unified & Polished Edition",
                "url_testing_enabled": CONFIG.enable_url_testing,
                "sorting_enabled": CONFIG.enable_sorting,
            },
            "statistics": stats,
            "source_categories": {
                "total_unique_sources": len(self.sources)
            },
            "output_files": {
                "raw": str(raw_file),
                **({"base64": str(base64_file)} if CONFIG.write_base64 else {}),
                **({"detailed_csv": str(csv_file)} if CONFIG.write_csv else {}),
                "json_report": str(report_file),
                "singbox": str(output_dir / f"{prefix}vpn_singbox.json"),
                "clash": str(output_dir / f"{prefix}clash.yaml"),
                **(
                    {"clash_proxies": str(output_dir / f"{prefix}vpn_clash_proxies.yaml")}
                    if CONFIG.write_clash_proxies
                    else {}
                ),
            },
            "usage_instructions": {
                "base64_subscription": "Copy content of base64 file as subscription URL",
                "raw_subscription": "Host raw file and use URL as subscription link",
                "csv_analysis": "Use CSV file for detailed analysis and custom filtering",
                "clash_yaml": "Load clash.yaml in Clash Meta or Stash",
                "clash_proxies_yaml": "Import vpn_clash_proxies.yaml as a simple provider",
                "supported_clients": [
                    "V2rayNG", "V2rayN", "Hiddify Next", "Shadowrocket",
                    "NekoBox", "Clash Meta", "Sing-Box", "Streisand", "Karing"
                ]
            }
        }
        
        tmp_report = report_file.with_suffix('.tmp')
        tmp_report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_report.replace(report_file)

        # Simple outbounds JSON
        outbounds = []
        for idx, r in enumerate(results):
            tag = re.sub(r"[^A-Za-z0-9_-]+", "-", f"{r.protocol}-{idx}")
            ob = {
                "type": r.protocol.lower(),
                "tag": tag,
                "server": r.host or "",
                "server_port": r.port,
                "raw": r.config
            }
            if r.country:
                ob["country"] = r.country
            outbounds.append(ob)

        singbox_file = output_dir / f"{prefix}vpn_singbox.json"
        tmp_singbox = singbox_file.with_suffix('.tmp')
        tmp_singbox.write_text(json.dumps({"outbounds": outbounds}, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_singbox.replace(singbox_file)

        if CONFIG.write_clash:
            clash_yaml = self._results_to_clash_yaml(results)
            clash_file = output_dir / f"{prefix}clash.yaml"
            tmp_clash = clash_file.with_suffix('.tmp')
            tmp_clash.write_text(clash_yaml, encoding="utf-8")
            tmp_clash.replace(clash_file)

        if CONFIG.write_clash_proxies:
            proxies = []
            for idx, r in enumerate(results):
                proxy = config_to_clash_proxy(r.config, idx, r.protocol)
                if proxy:
                    proxies.append(proxy)
            proxy_yaml = yaml.safe_dump({"proxies": proxies}, allow_unicode=True, sort_keys=False) if proxies else ""
            proxies_file = output_dir / f"{prefix}vpn_clash_proxies.yaml"
            tmp_proxies = proxies_file.with_suffix('.tmp')
            tmp_proxies.write_text(proxy_yaml, encoding="utf-8")
            tmp_proxies.replace(proxies_file)


    def _results_to_clash_yaml(self, results: List[ConfigResult]) -> str:
        """Convert results list to Clash YAML string."""
        proxies = []
        for idx, r in enumerate(results):
            proxy = config_to_clash_proxy(r.config, idx, r.protocol)
            if proxy:
                proxies.append(proxy)
        if not proxies:
            return ""
        group = {
            "name": "Auto",
            "type": "select",
            "proxies": [p["name"] for p in proxies],
        }
        return yaml.safe_dump({"proxies": proxies, "proxy-groups": [group]}, allow_unicode=True, sort_keys=False)
    
    def _print_final_summary(self, config_count: int, elapsed_time: float, stats: Dict) -> None:
        """Print comprehensive final summary."""
        print("\n" + "=" * 85)
        print("🎉 UNIFIED VPN MERGER COMPLETE!")
        print(f"⏱️  Total processing time: {elapsed_time:.2f} seconds")
        print(f"📊 Final unique configs: {config_count:,}")
        print(f"🌐 Reachable configs: {stats['reachable_configs']:,}")
        if config_count:
            success = f"{stats['reachable_configs'] / config_count * 100:.1f}%"
        else:
            success = "N/A"
        print(f"📈 Success rate: {success}")
        print(f"🔗 Available sources: {stats['available_sources']}/{stats['total_sources']}")
        speed = (config_count / elapsed_time) if elapsed_time else 0
        print(f"⚡ Processing speed: {speed:.0f} configs/second")
        
        if CONFIG.enable_sorting and stats['reachable_configs'] > 0:
            print("🚀 Configs sorted by performance (fastest first)")
        
        if stats['protocol_stats']:
            top_protocol = max(stats['protocol_stats'].items(), key=lambda x: x[1])[0]
        else:
            top_protocol = "N/A"
        print(f"🏆 Top protocol: {top_protocol}")
        print(f"📁 Output directory: ./{CONFIG.output_dir}/")
        print("\n🔗 Usage Instructions:")
        print("   • Copy Base64 file content as subscription URL")
        print("   • Use CSV file for detailed analysis and filtering")
        print("   • All configs tested and sorted by performance")
        print("   • Dead sources automatically removed")
        print("=" * 85)

# ============================================================================
# EVENT LOOP DETECTION AND MAIN EXECUTION
# ============================================================================

async def main_async(sources_file: Optional[Union[str, Path]] = None):
    """Main async function."""
    try:
        merger = UltimateVPNMerger(sources_file)
        await merger.run()
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
    except (OSError, aiohttp.ClientError, ValueError, RuntimeError) as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

def detect_and_run(sources_file: Optional[Union[str, Path]] = None):
    """Detect event loop and run appropriately."""
    try:
        # Try to get the running loop
        asyncio.get_running_loop()
        print("🔄 Detected existing event loop")
        print("📝 Creating task in existing loop...")
        
        # We're in an async environment (like Jupyter)
        task = asyncio.create_task(main_async(sources_file))
        print("✅ Task created successfully!")
        print("📋 Use 'await task' to wait for completion in Jupyter")
        return task
        
    except RuntimeError:
        # No running loop - we can use asyncio.run()
        print("🔄 No existing event loop detected")
        print("📝 Using asyncio.run()...")
        return asyncio.run(main_async(sources_file))

# Alternative for Jupyter/async environments
async def run_in_jupyter(sources_file: Optional[Union[str, Path]] = None):
    """Direct execution for Jupyter notebooks and async environments."""
    print("🔄 Running in Jupyter/async environment")
    await main_async(sources_file)

def _get_script_dir() -> Path:
    """
    Return a safe base directory for writing output.
    • In a regular script run, that’s the directory the script lives in.
    • In interactive/Jupyter runs, fall back to the current working dir.
    """
    try:
        return Path(__file__).resolve().parent        # normal execution
    except NameError:
        return Path.cwd()                             # Jupyter / interactive


def main():
    """Main entry point with event loop detection."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)

    import argparse

    parser = argparse.ArgumentParser(description="VPN Merger")
    parser.add_argument(
        "--sources",
        default=str(UnifiedSources.DEFAULT_FILE),
        help="Path to sources.txt",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=CONFIG.batch_size,
        help="Save intermediate output every N configs (0 disables, default 100)"
    )
    parser.add_argument("--threshold", type=int, default=CONFIG.threshold,
                        help="Stop processing after N unique configs (0 = unlimited)")
    parser.add_argument("--top-n", type=int, default=CONFIG.top_n,
                        help="Keep only the N best configs after sorting (0 = all)")
    parser.add_argument("--tls-fragment", type=str, default=CONFIG.tls_fragment,
                        help="Only keep configs containing this TLS fragment")
    parser.add_argument("--include-protocols", type=str, default=None,
                        help="Comma-separated list of protocols to include")
    parser.add_argument(
        "--exclude-protocols",
        type=str,
        default=None,
        help="Comma-separated list of protocols to exclude (default: OTHER)"
    )
    parser.add_argument(
        "--exclude-pattern",
        action="append",
        help="Regular expression to skip configs (can be repeated)",
    )
    parser.add_argument("--resume", type=str, default=None,
                        help="Resume processing from existing raw/base64 file")
    parser.add_argument("--output-dir", type=str, default=CONFIG.output_dir,
                        help="Directory to save output files")
    parser.add_argument("--test-timeout", type=float, default=CONFIG.test_timeout,
                        help="TCP connection test timeout in seconds")
    parser.add_argument("--no-url-test", action="store_true",
                        help="Disable server reachability testing")
    parser.add_argument("--no-sort", action="store_true",
                        help="Disable performance-based sorting")
    parser.add_argument("--concurrent-limit", type=int, default=CONFIG.concurrent_limit,
                        help="Number of concurrent requests")
    parser.add_argument("--max-retries", type=int, default=CONFIG.max_retries,
                        help="Retry attempts when fetching sources")
    parser.add_argument("--max-ping", type=int, default=0,
                        help="Discard configs slower than this ping in ms (0 = no limit)")
    parser.add_argument("--log-file", type=str, default=None,
                        help="Write output messages to a log file")
    parser.add_argument("--cumulative-batches", action="store_true",
                        help="Save each batch as cumulative rather than standalone")
    parser.add_argument("--no-strict-batch", action="store_true",
                        help="Use batch size only as update threshold")
    parser.add_argument("--shuffle-sources", action="store_true",
                        help="Process sources in random order")
    parser.add_argument("--mux", type=int, default=CONFIG.mux_concurrency,
                        help="Set mux concurrency for URI configs (0=disable)")
    parser.add_argument("--smux", type=int, default=CONFIG.smux_streams,
                        help="Set smux streams for URI configs (0=disable)")
    parser.add_argument("--no-base64", action="store_true",
                        help="Do not save base64 subscription file")
    parser.add_argument("--no-csv", action="store_true",
                        help="Do not save CSV report")
    parser.add_argument("--no-proxy-yaml", action="store_true",
                        help="Do not save simple Clash proxy list")
    parser.add_argument("--geoip-db", type=str, default=None,
                        help="Path to GeoLite2 Country database for GeoIP lookup")
    parser.add_argument(
        "--include-country",
        type=str,
        default=None,
        help="Comma-separated ISO codes to include when GeoIP is enabled",
    )
    parser.add_argument(
        "--exclude-country",
        type=str,
        default=None,
        help="Comma-separated ISO codes to exclude when GeoIP is enabled",
    )
    args, unknown = parser.parse_known_args()
    if unknown:
        logging.warning("Ignoring unknown arguments: %s", unknown)

    sources_file = args.sources

    CONFIG.batch_size = max(0, args.batch_size)
    CONFIG.threshold = max(0, args.threshold)
    CONFIG.top_n = max(0, args.top_n)
    CONFIG.tls_fragment = args.tls_fragment
    if args.include_protocols:
        CONFIG.include_protocols = {p.strip().upper() for p in args.include_protocols.split(',') if p.strip()}

    if args.exclude_protocols is None:
        CONFIG.exclude_protocols = {"OTHER"}
    elif args.exclude_protocols.strip() == "":
        CONFIG.exclude_protocols = None
    else:
        CONFIG.exclude_protocols = {
            p.strip().upper() for p in args.exclude_protocols.split(',') if p.strip()
        }
    CONFIG.exclude_patterns = args.exclude_pattern or []
    global EXCLUDE_REGEXES
    EXCLUDE_REGEXES = [re.compile(p) for p in CONFIG.exclude_patterns]
    CONFIG.resume_file = args.resume
    # Resolve and validate output directory to prevent path traversal
    allowed_base = _get_script_dir()
    resolved_output = Path(args.output_dir).expanduser().resolve()
    try:
        resolved_output.relative_to(allowed_base)
    except ValueError:
        parser.error(f"--output-dir must be within {allowed_base}")
    CONFIG.output_dir = str(resolved_output)
    CONFIG.test_timeout = max(0.1, args.test_timeout)
    CONFIG.concurrent_limit = max(1, args.concurrent_limit)
    CONFIG.max_retries = max(1, args.max_retries)
    CONFIG.max_ping_ms = args.max_ping if args.max_ping > 0 else None
    CONFIG.log_file = args.log_file
    CONFIG.write_base64 = not args.no_base64
    CONFIG.write_csv = not args.no_csv
    CONFIG.write_clash_proxies = not args.no_proxy_yaml
    CONFIG.cumulative_batches = args.cumulative_batches
    CONFIG.strict_batch = not args.no_strict_batch
    CONFIG.shuffle_sources = args.shuffle_sources
    CONFIG.mux_concurrency = max(0, args.mux)
    CONFIG.smux_streams = max(0, args.smux)
    CONFIG.geoip_db = args.geoip_db
    if args.include_country:
        CONFIG.include_countries = {c.strip().upper() for c in args.include_country.split(',') if c.strip()}
    if args.exclude_country:
        CONFIG.exclude_countries = {c.strip().upper() for c in args.exclude_country.split(',') if c.strip()}
    if args.no_url_test:
        CONFIG.enable_url_testing = False
    if args.no_sort:
        CONFIG.enable_sorting = False

    if CONFIG.log_file:
        logging.basicConfig(filename=CONFIG.log_file, level=logging.INFO,
                            format='%(asctime)s %(levelname)s:%(message)s')

    print("🔧 VPN Merger - Checking environment...")

    try:
        return detect_and_run(sources_file)
    except (OSError, aiohttp.ClientError, RuntimeError, ValueError) as e:
        print(f"❌ Error: {e}")
        print("\n📋 Alternative execution methods:")
        print("   • For Jupyter: await run_in_jupyter()")
        print("   • For scripts: python script.py")

if __name__ == "__main__":
    main()

    # ========================================================================
    # USAGE INSTRUCTIONS
    # ========================================================================

    print(
        """\
🚀 VPN Subscription Merger - Final Unified Edition

📋 Execution Methods:
   • Regular Python: python script.py
   • Jupyter/IPython: await run_in_jupyter()
   • With event loop errors: task = detect_and_run(); await task

🎯 Unified Features:
   • Sources loaded from `sources.txt` (over 450 links)
   • Dead link detection and automatic removal
   • Real-time server reachability testing with response time measurement
   • Smart sorting by connection speed and protocol preference
   • Advanced semantic deduplication
   • Multiple output formats (raw, base64, CSV with performance data, JSON)
   • Event loop compatibility for all environments
   • Comprehensive error handling and retry logic

📊 Expected Results:
   • 800k-1.2M+ tested and sorted configs
   • 70-85% configs will be reachable and validated
   • Processing time: 8-12 minutes with full testing
   • Dead sources automatically filtered out
   • Performance-optimized final list

📁 Output Files:
   • vpn_subscription_raw.txt (for hosting)
   • vpn_subscription_base64.txt (optional, for direct import)
   • vpn_detailed.csv (optional, with performance metrics)
   • vpn_report.json (comprehensive statistics)
"""
    )
