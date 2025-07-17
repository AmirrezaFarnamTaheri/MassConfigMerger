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
import signal
import logging
import random
import re
import sys
import time
import argparse
import os
import json
import base64
import binascii
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from urllib.parse import urlparse, parse_qs
from tqdm import tqdm

try:
    import colorama
    colorama.just_fix_windows_console()
except Exception:
    pass

from .source_fetcher import (
    fetch_text,
    parse_first_configs,
    UnifiedSources,
    AsyncSourceFetcher,
)
from .result_processor import (
    CONFIG,
    ConfigResult,
    EnhancedConfigProcessor,
)
from .output_writer import (
    generate_comprehensive_outputs,
    EXCLUDE_REGEXES as OUTPUT_EXCLUDE_REGEXES,
    upload_files_to_gist,
    write_upload_links,
)
from .clash_utils import config_to_clash_proxy, flag_emoji, build_clash_config
from .utils import print_public_source_warning, choose_proxy

try:
    import aiohttp
except ImportError as exc:
    raise ImportError(
        "Missing optional dependency 'aiohttp'. "
        "Run `pip install -r requirements.txt` before running this script."
    ) from exc

# Event loop compatibility fix
try:
    import nest_asyncio
    import os  # noqa: F811
    if __name__ == "__main__" or os.environ.get("NEST_ASYNCIO") == "1":
        nest_asyncio.apply()
        if __name__ == "__main__":
            print("✅ Applied nest_asyncio patch for event loop compatibility")
except ImportError as exc:
    raise ImportError(
        "Missing optional dependency 'nest_asyncio'. "
        "Run `pip install -r requirements.txt` before running this script."
    ) from exc

from .config import load_config

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


# Reuse global regex list from output_writer
EXCLUDE_REGEXES: List[re.Pattern] = OUTPUT_EXCLUDE_REGEXES
INCLUDE_REGEXES: List[re.Pattern] = []

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
        self.seen_hashes_lock = asyncio.Lock()
        self.fetcher = AsyncSourceFetcher(
            self.processor,
            self.seen_hashes,
            self.seen_hashes_lock,
            self._update_history,
            proxy=choose_proxy(CONFIG),
        )
        self.batch_counter = 0
        self.next_batch_threshold = CONFIG.save_every if CONFIG.save_every else float('inf')
        self.start_time = 0.0
        self.available_sources: List[str] = []
        self.all_results: List[ConfigResult] = []
        self.stop_fetching = False
        self.saved_hashes: Set[str] = set()
        self.cumulative_unique: List[ConfigResult] = []
        self.last_processed_index = 0
        self.last_saved_count = 0
        self.current_progress: Optional[tqdm] = None
        self._file_lock = asyncio.Lock()
        self._history_lock = asyncio.Lock()
        # Store proxy history in configurable location
        hist_path = Path(CONFIG.history_file)
        if not hist_path.is_absolute():
            hist_path = Path(CONFIG.output_dir) / hist_path
        self.history_path = hist_path
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.proxy_history = json.loads(self.history_path.read_text())
        except (OSError, json.JSONDecodeError):
            self.proxy_history = {}

    async def _update_history(
        self,
        config_hash: str,
        success: bool,
        latency: Optional[float],
    ) -> None:
        async with self._history_lock:
            entry = self.proxy_history.setdefault(
                config_hash,
                {
                    "last_latency_ms": None,
                    "last_seen_online_utc": None,
                    "successful_checks": 0,
                    "total_checks": 0,
                },
            )
            entry["total_checks"] += 1
            if success:
                entry["successful_checks"] += 1
                entry["last_seen_online_utc"] = datetime.now(timezone.utc).isoformat()
            entry["last_latency_ms"] = round(latency * 1000) if latency is not None else None

    async def _save_proxy_history(self) -> None:
        async with self._file_lock:
            tmp = self.history_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.proxy_history, indent=2))
            tmp.replace(self.history_path)

    def _register_signal_handlers(self) -> None:
        """Set up SIGINT handler to close progress bars gracefully."""
        def handler() -> None:
            self.stop_fetching = True
            if self.current_progress:
                self.current_progress.close()
                if self.fetcher.progress is self.current_progress:
                    self.fetcher.progress = None
                self.current_progress = None
            if self.fetcher.progress:
                self.fetcher.progress.close()
                self.fetcher.progress = None
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGINT, handler)
        except (RuntimeError, NotImplementedError, AttributeError):
            signal.signal(signal.SIGINT, lambda s, f: handler())

    async def _load_existing_results(self, path: str) -> List[ConfigResult]:
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
            country = await self.processor.lookup_country(host) if host else None
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
            async with self.seen_hashes_lock:
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
        
        self._register_signal_handlers()
        start_time = time.time()
        self.start_time = start_time

        if CONFIG.resume_file:
            print(f"🔄 Loading existing configs from {CONFIG.resume_file} ...")
            self.all_results.extend(
                await self._load_existing_results(CONFIG.resume_file)
            )
            print(f"   ✔ Loaded {len(self.all_results)} configs from resume file")
            await self._maybe_save_batch()

        # Step 1: Test source availability and remove dead links
        print("🔄 [1/6] Testing source availability and removing dead links...")
        self.available_sources = await self._test_and_filter_sources()

        if CONFIG.enable_url_testing:
            print("\n🔎 Running pre-flight connectivity check...")
            ok = await self._preflight_connectivity_check(10)
            if not ok:
                sys.stderr.write(
                    "❌ Critical Error: All initial connectivity tests failed. Please check your internet connection and firewall, then try again.\n"
                )
                sys.exit(1)

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

        await self._save_proxy_history()

        self._print_final_summary(len(unique_results), time.time() - self.start_time, stats)

        elapsed = time.time() - start_time
        summary = (
            f"Sources checked: {len(self.available_sources)} | "
            f"Configs fetched: {len(self.all_results)} | "
            f"Unique configs: {len(unique_results)} | "
            f"Elapsed: {elapsed:.1f}s"
        )
        print(summary)
        logging.info(summary)

        # Clean up tester resources
        await self.processor.tester.close()
    
    async def _test_and_filter_sources(self) -> List[str]:
        """Test all sources for availability and filter out dead links."""
        assert self.fetcher.session is not None

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

    async def _preflight_connectivity_check(self, max_tests: int = 5) -> bool:
        """Quickly test a handful of configs to verify connectivity."""
        if not self.available_sources:
            return False

        assert self.fetcher.session is not None
        tested = 0
        proc = EnhancedConfigProcessor()

        progress = tqdm(total=max_tests, desc="Testing", unit="cfg", leave=False)
        self.current_progress = progress

        for url in self.available_sources:
            if tested >= max_tests:
                break

            text = await fetch_text(
                self.fetcher.session,
                url,
                int(CONFIG.request_timeout),
                retries=1,
                base_delay=0.5,
                proxy=choose_proxy(CONFIG),
            )
            if not text:
                continue

            configs = parse_first_configs(text, max_tests - tested)
            for cfg in configs:
                host, port = proc.extract_host_port(cfg)
                if host and port:
                    ping = await proc.test_connection(host, port)
                    tested += 1
                    progress.update(1)
                    if ping is not None:
                        progress.close()
                        self.current_progress = None
                        return True
                    if tested >= max_tests:
                        break

        progress.close()
        self.current_progress = None

        return False
    
    async def _fetch_all_sources(self, available_sources: List[str]) -> List[ConfigResult]:
        """Fetch all configs from available sources."""
        # Append results directly to self.all_results so that _maybe_save_batch
        # sees the running total and can save incremental batches.
        successful_sources = 0
        progress = tqdm(total=0, desc="Testing", unit="cfg", leave=False)
        self.fetcher.progress = progress
        self.current_progress = progress

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
                if results:
                    progress.total += len(results)
                    progress.refresh()
                    progress.set_postfix(
                        processed=progress.n,
                        remaining=progress.total - progress.n,
                        refresh=False,
                    )

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
            self.fetcher.progress = None
            self.current_progress = None
            progress.close()
            await self.fetcher.close()

        # Return the accumulated list for backward compatibility
        return self.all_results

    async def _maybe_save_batch(self) -> None:
        """Save intermediate output based on batch settings."""
        if CONFIG.save_every <= 0:
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
            if INCLUDE_REGEXES and not any(rx.search(text) for rx in INCLUDE_REGEXES):
                continue
            if CONFIG.enable_url_testing and r.ping_time is None:
                continue
            h = self.processor.create_semantic_hash(r.config)
            if h not in self.saved_hashes:
                self.saved_hashes.add(h)
                self.cumulative_unique.append(r)

        if CONFIG.strict_batch:
            while len(self.cumulative_unique) - self.last_saved_count >= CONFIG.save_every:
                self.batch_counter += 1
                if CONFIG.cumulative_batches:
                    batch_results = self.cumulative_unique[:]
                else:
                    start = self.last_saved_count
                    end = start + CONFIG.save_every
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

                if CONFIG.stop_after_found > 0 and len(self.cumulative_unique) >= CONFIG.stop_after_found:
                    print(f"\n⏹️  Threshold of {CONFIG.stop_after_found} configs reached. Stopping early.")
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

                self.next_batch_threshold += CONFIG.save_every

                if CONFIG.stop_after_found > 0 and len(self.cumulative_unique) >= CONFIG.stop_after_found:
                    print(f"\n⏹️  Threshold of {CONFIG.stop_after_found} configs reached. Stopping early.")
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
            if INCLUDE_REGEXES and not any(r.search(text) for r in INCLUDE_REGEXES):
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
        
        def sort_key_latency(result: ConfigResult) -> Tuple:
            is_reachable = 1 if result.is_reachable else 0
            ping_time = result.ping_time if result.ping_time is not None else float('inf')
            protocol_rank = protocol_priority.get(result.protocol, 13)
            return (-is_reachable, ping_time, protocol_rank)

        def sort_key_reliability(result: ConfigResult) -> Tuple:
            h = self.processor.create_semantic_hash(result.config)
            hist = self.proxy_history.get(h, {})
            total = hist.get("total_checks", 0)
            success = hist.get("successful_checks", 0)
            reliability = success / total if total else 0
            ping_time = result.ping_time if result.ping_time is not None else float('inf')
            protocol_rank = protocol_priority.get(result.protocol, 13)
            return (-reliability, ping_time, protocol_rank)

        key_func = sort_key_latency if CONFIG.sort_by != "reliability" else sort_key_reliability

        progress = tqdm(total=len(results), desc="Testing", unit="cfg", leave=False)
        self.current_progress = progress
        keyed = []
        try:
            for r in results:
                keyed.append((key_func(r), r))
                progress.update(1)
                progress.set_postfix(
                    processed=progress.n,
                    remaining=progress.total - progress.n,
                    refresh=False,
                )
        finally:
            progress.close()
            self.current_progress = None

        sorted_results = [r for _, r in sorted(keyed, key=lambda x: x[0])]

        if CONFIG.sort_by == "reliability":
            print("   🚀 Sorted by reliability")
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

    def _parse_extra_params(self, link: str) -> Dict[str, Any]:
        """Extract additional parameters for sing-box outbounds."""
        try:
            p = urlparse(link)
            q = parse_qs(p.query)
            scheme = p.scheme.lower()
            extra: Dict[str, Any] = {}
            if scheme in {"vless", "reality"}:
                pbk = (
                    q.get("pbk")
                    or q.get("public-key")
                    or q.get("publicKey")
                    or q.get("public_key")
                    or q.get("publickey")
                )
                sid = (
                    q.get("sid")
                    or q.get("short-id")
                    or q.get("shortId")
                    or q.get("short_id")
                    or q.get("shortid")
                )
                spider = q.get("spiderX") or q.get("spider-x") or q.get("spider_x")
                if pbk:
                    extra["publicKey"] = pbk[0]
                if sid:
                    extra["shortId"] = sid[0]
                if spider:
                    extra["spiderX"] = spider[0]
            elif scheme == "tuic":
                uuid = p.username or q.get("uuid", [None])[0]
                password = p.password or q.get("password", [None])[0]
                if uuid:
                    extra["uuid"] = uuid
                if password:
                    extra["password"] = password
                if "alpn" in q:
                    extra["alpn"] = q["alpn"][0]
                cc = q.get("congestion-control") or q.get("congestion_control")
                if cc:
                    extra["congestion-control"] = cc[0]
                mode = q.get("udp-relay-mode") or q.get("udp_relay_mode")
                if mode:
                    extra["udp-relay-mode"] = mode[0]
            elif scheme in {"hy2", "hysteria2"}:
                passwd = p.password or q.get("password", [None])[0]
                if p.username and not passwd:
                    passwd = p.username
                if passwd:
                    extra["password"] = passwd
                for key in (
                    "auth",
                    "peer",
                    "sni",
                    "insecure",
                    "alpn",
                    "obfs",
                    "obfs-password",
                ):
                    if key in q:
                        extra[key.replace("-", "_")] = q[key][0]
                up_keys = ["upmbps", "up", "up_mbps"]
                down_keys = ["downmbps", "down", "down_mbps"]
                for k in up_keys:
                    if k in q:
                        extra["upmbps"] = q[k][0]
                        break
                for k in down_keys:
                    if k in q:
                        extra["downmbps"] = q[k][0]
                        break
            return extra
        except Exception:
            return {}
    
    async def _generate_comprehensive_outputs(
        self,
        results: List[ConfigResult],
        stats: Dict,
        start_time: float,
        prefix: str = "",
    ) -> None:
        await generate_comprehensive_outputs(self, results, stats, start_time, prefix)


    def _results_to_clash_yaml(self, results: List[ConfigResult]) -> str:
        """Convert results list to Clash YAML string."""
        proxies = []
        for idx, r in enumerate(results):
            proxy = config_to_clash_proxy(r.config, idx, r.protocol)
            if not proxy:
                continue
            latency = (
                f"{int(r.ping_time * 1000)}ms" if r.ping_time is not None else "?"
            )
            domain = urlparse(r.source_url).hostname or "src"
            cc = r.country or "??"
            emoji = flag_emoji(r.country)
            proxy["name"] = f"{emoji} {cc} - {domain} - {latency}"
            proxies.append(proxy)

        return build_clash_config(proxies)
    
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
        if CONFIG.sort_by == "reliability":
            total_checks = sum(h.get("total_checks", 0) for h in self.proxy_history.values())
            successes = sum(h.get("successful_checks", 0) for h in self.proxy_history.values())
            if total_checks:
                avg_rel = successes / total_checks * 100
                reliability = f"{avg_rel:.1f}% over {total_checks} checks"
            else:
                reliability = "N/A over 0 checks"
            print(f"⭐ Average reliability: {reliability}")
        speed = (config_count / elapsed_time) if elapsed_time else 0

        rows = [
            ("Total configs", f"{config_count:,}"),
            ("Reachable", f"{stats['reachable_configs']:,}"),
            ("Success rate", success),
            ("Sources", f"{stats['available_sources']}/{stats['total_sources']}"),
            ("Speed", f"{speed:.0f} cfg/s"),
        ]
        print("\033[95m\nSUMMARY\033[0m")
        print("\033[94m┌────────────────────┬──────────────┐\033[0m")
        for label, value in rows:
            print(f"\033[94m│ {label:<18} │\033[92m {value:<12}\033[94m│\033[0m")
        print("\033[94m└────────────────────┴──────────────┘\033[0m")
        if CONFIG.enable_sorting and stats['reachable_configs'] > 0:
            print("🚀 Configs sorted by performance (fastest first)")
        if stats['protocol_stats']:
            top_protocol = max(stats['protocol_stats'].items(), key=lambda x: x[1])[0]
        else:
            top_protocol = "N/A"
        print(f"🏆 Top protocol: {top_protocol}")
        print(f"📁 Output directory: ./{CONFIG.output_dir}/")

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

def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    """Return an argument parser configured for the VPN merger."""
    if parser is None:
        parser = argparse.ArgumentParser(description="VPN Merger")

    parser.add_argument(
        "--sources",
        default=str(UnifiedSources.DEFAULT_FILE),
        help="Path to sources.txt",
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=CONFIG.save_every,
        help="Save intermediate output every N configs (0 disables, default 100)",
        dest="save_every",
    )
    parser.add_argument(
        "--stop-after-found",
        type=int,
        default=CONFIG.stop_after_found,
        help="Stop processing after N unique configs (0 = unlimited)",
        dest="stop_after_found",
    )
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
    parser.add_argument(
        "--include-pattern",
        action="append",
        help="Regular expression configs must match (can be repeated)",
    )
    parser.add_argument("--resume", type=str, default=None,
                        help="Resume processing from existing raw/base64 file")
    parser.add_argument("--output-dir", type=str, default=CONFIG.output_dir,
                        help="Directory to save output files")
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=CONFIG.connect_timeout,
        help="TCP connect timeout in seconds",
    )
    parser.add_argument("--no-url-test", action="store_true",
                        help="Disable server reachability testing")
    parser.add_argument("--no-sort", action="store_true",
                        help="Disable performance-based sorting")
    parser.add_argument(
        "--sort-by",
        choices=["latency", "reliability"],
        default=CONFIG.sort_by,
        help="Sorting method when enabled",
    )
    parser.add_argument("--concurrent-limit", type=int, default=CONFIG.concurrent_limit,
                        help="Number of concurrent requests")
    parser.add_argument("--max-retries", type=int, default=CONFIG.max_retries,
                        help="Retry attempts when fetching sources")
    parser.add_argument(
        "--max-ping",
        type=int,
        default=CONFIG.max_ping_ms,
        help="Discard configs slower than this ping in ms (0 = no limit)",
    )
    parser.add_argument("--log-file", type=str, default=None,
                        help="Write output messages to a log file")
    parser.add_argument("--cumulative-batches", action="store_true",
                        help="Save each batch as cumulative rather than standalone")
    parser.add_argument("--no-strict-batch", action="store_true",
                        help="Use save-every only as update threshold")
    parser.add_argument("--shuffle-sources", action="store_true",
                        help="Process sources in random order")
    parser.add_argument("--mux", type=int, default=CONFIG.mux_concurrency,
                        help="Set mux concurrency for URI configs (0=disable)")
    parser.add_argument("--smux", type=int, default=CONFIG.smux_streams,
                        help="Set smux streams for URI configs (0=disable)")
    parser.add_argument(
        "--history-file",
        type=str,
        default=None,
        help="Path to proxy history JSON file",
    )
    parser.add_argument(
        "--http-proxy",
        type=str,
        default=None,
        help="HTTP proxy URL overriding config/env",
    )
    parser.add_argument(
        "--socks-proxy",
        type=str,
        default=None,
        help="SOCKS proxy URL overriding config/env",
    )
    parser.add_argument("--no-base64", action="store_true",
                        help="Do not save base64 subscription file")
    parser.add_argument("--no-csv", action="store_true",
                        help="Do not save CSV report")
    parser.add_argument("--write-html", action="store_true",
                        help="Generate vpn_report.html")
    parser.add_argument("--no-proxy-yaml", action="store_true",
                        help="Do not save simple Clash proxy list")
    parser.add_argument(
        "--output-surge",
        metavar="FILE",
        type=str,
        default=None,
        help="Write Surge formatted proxy list to FILE",
    )
    parser.add_argument(
        "--output-qx",
        metavar="FILE",
        type=str,
        default=None,
        help="Write Quantumult X formatted proxy list to FILE",
    )
    parser.add_argument(
        "--output-xyz",
        metavar="FILE",
        type=str,
        default=None,
        help="Write XYZ formatted proxy list to FILE",
    )
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
    parser.add_argument(
        "--help-extra",
        action="store_true",
        help="Show extended usage information and exit",
    )
    parser.add_argument(
        "--upload-gist",
        action="store_true",
        help="upload output files to a GitHub Gist",
    )

    return parser


def main(args: argparse.Namespace | None = None) -> int:
    """Main entry point with event loop detection."""
    print_public_source_warning()
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)

    if args is None:
        parser = build_parser()
        args, unknown = parser.parse_known_args()
        if args.help_extra:
            parser.print_help()
            print("\nFor a complete tutorial see docs/tutorial.md")
            return 0
        if unknown:
            logging.warning("Ignoring unknown arguments: %s", unknown)
    else:
        parser = None

    try:
        load_config()
    except ValueError:
        print("Config file not found. Copy config.yaml.example to config.yaml.")
        sys.exit(1)

    sources_file = args.sources

    CONFIG.save_every = max(0, args.save_every)
    CONFIG.stop_after_found = max(0, args.stop_after_found)
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
    CONFIG.include_patterns = args.include_pattern or []
    global EXCLUDE_REGEXES
    EXCLUDE_REGEXES = [re.compile(p) for p in CONFIG.exclude_patterns]
    global INCLUDE_REGEXES
    INCLUDE_REGEXES = [re.compile(p) for p in CONFIG.include_patterns]
    CONFIG.resume_file = args.resume
    # Resolve and create output directory if needed
    resolved_output = Path(args.output_dir).expanduser().resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    CONFIG.output_dir = str(resolved_output)
    CONFIG.connect_timeout = max(0.1, args.connect_timeout)
    CONFIG.concurrent_limit = max(1, args.concurrent_limit)
    CONFIG.max_retries = max(1, args.max_retries)
    CONFIG.max_ping_ms = args.max_ping
    CONFIG.log_file = args.log_file
    CONFIG.write_base64 = not args.no_base64
    CONFIG.write_csv = not args.no_csv
    CONFIG.write_html = args.write_html
    CONFIG.write_clash_proxies = not args.no_proxy_yaml
    CONFIG.surge_file = args.output_surge
    CONFIG.qx_file = args.output_qx
    CONFIG.xyz_file = args.output_xyz
    CONFIG.cumulative_batches = args.cumulative_batches
    CONFIG.strict_batch = not args.no_strict_batch
    CONFIG.shuffle_sources = args.shuffle_sources
    CONFIG.mux_concurrency = max(0, args.mux)
    CONFIG.smux_streams = max(0, args.smux)
    if args.history_file is not None:
        CONFIG.history_file = args.history_file
    if args.http_proxy is not None:
        CONFIG.HTTP_PROXY = args.http_proxy
    if args.socks_proxy is not None:
        CONFIG.SOCKS_PROXY = args.socks_proxy
    CONFIG.geoip_db = args.geoip_db
    if args.include_country:
        CONFIG.include_countries = {c.strip().upper() for c in args.include_country.split(',') if c.strip()}
    if args.exclude_country:
        CONFIG.exclude_countries = {c.strip().upper() for c in args.exclude_country.split(',') if c.strip()}
    if args.no_url_test:
        CONFIG.enable_url_testing = False
    if args.no_sort:
        CONFIG.enable_sorting = False
    CONFIG.sort_by = args.sort_by

    if CONFIG.log_file:
        logging.basicConfig(filename=CONFIG.log_file, level=logging.INFO,
                            format='%(asctime)s %(levelname)s:%(message)s')

    print("🔧 VPN Merger - Checking environment...")

    try:
        detect_and_run(sources_file)
    except (OSError, aiohttp.ClientError, RuntimeError, ValueError) as e:
        print(f"❌ Error: {e}")
        print("\n📋 Alternative execution methods:")
        print("   • For Jupyter: await run_in_jupyter()")
        print("   • For scripts: python script.py")
        return 1

    if args.upload_gist:
        token = CONFIG.github_token or os.environ.get("GITHUB_TOKEN")
        if not token:
            print("GitHub token not provided. Set github_token in config or GITHUB_TOKEN env var")
        else:
            report_file = Path(CONFIG.output_dir) / "vpn_report.json"
            try:
                data = json.loads(report_file.read_text())
                file_paths = [Path(p) for p in data.get("output_files", {}).values()]
            except Exception:
                file_paths = []
            if file_paths:
                links = asyncio.run(upload_files_to_gist(file_paths, token))
                write_upload_links(links, Path(CONFIG.output_dir))
                print("Uploaded files. Links saved to", Path(CONFIG.output_dir) / "upload_links.txt")

    return 0
