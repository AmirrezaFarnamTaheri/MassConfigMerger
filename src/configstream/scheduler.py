"""Automated testing scheduler for periodic VPN node testing."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import Settings
from .vpn_merger import run_merger
from .core.types import ConfigResult


logger = logging.getLogger(__name__)

class TestScheduler:
    """Manages periodic testing of VPN configurations."""

    def __init__(self, settings: Settings, output_dir: Path):
        self.settings = settings
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scheduler = AsyncIOScheduler()
        self.sources_file = Path(settings.sources.sources_file)
        self.current_results_file = self.output_dir / "current_results.json"
        self.history_file = self.output_dir / "history.jsonl"

    def _serialize_result(self, result: ConfigResult, timestamp: str) -> dict:
        """Convert a ConfigResult to a JSON-serializable dict."""
        return {
            "config": result.config,
            "protocol": result.protocol,
            "ping_ms": int(result.ping_time * 1000) if result.ping_time is not None else -1,
            "country": result.country or "Unknown",
            "city": "N/A",
            "organization": result.isp or "Unknown",
            "ip": result.host,
            "port": result.port,
            "is_blocked": result.is_blocked,
            "timestamp": timestamp,
            "packet_loss_percent": result.packet_loss_percent,
            "jitter_ms": result.jitter_ms,
            "download_mbps": result.download_mbps,
            "upload_mbps": result.upload_mbps,
            "quality_score": result.quality_score,
            "network_stable": result.network_stable
        }

    async def run_advanced_tests_on_top_nodes(
        self,
        results: list[ConfigResult],
    ) -> list[ConfigResult]:
        """Run bandwidth and quality tests on top N nodes."""
        from .testing.bandwidth_tester import BandwidthTester
        from .testing.network_quality import NetworkQualityTester
        from .core.local_proxy import LocalProxy

        top_n = self.settings.testing.advanced_test_top_n
        successful = [r for r in results if r.is_reachable]
        top_nodes = sorted(successful, key=lambda x: x.ping_time or float('inf'))[:top_n]

        logger.info(f"Running advanced tests on top {len(top_nodes)} nodes")

        for i, node in enumerate(top_nodes, 1):
            logger.info(f"[{i}/{len(top_nodes)}] Advanced testing on {node.host}:{node.port}")
            local_proxy = None
            try:
                if self.settings.testing.test_network_quality and node.host:
                    quality_tester = NetworkQualityTester(test_count=10)
                    quality_result = await quality_tester.test_quality(node.host, node.port)
                    node.packet_loss_percent = quality_result.packet_loss_percent
                    node.jitter_ms = quality_result.jitter_ms
                    node.quality_score = quality_result.quality_score
                    node.network_stable = quality_result.is_stable

                if self.settings.testing.test_bandwidth:
                    local_proxy = LocalProxy.from_config(node.config)
                    await local_proxy.start()
                    proxy_url = local_proxy.http_url
                    bandwidth_tester = BandwidthTester(proxy=proxy_url)
                    bandwidth_result = await bandwidth_tester.test_full()
                    node.download_mbps = bandwidth_result.download_mbps
                    node.upload_mbps = bandwidth_result.upload_mbps
            except Exception as e:
                logger.error(f"Advanced test failed for {node.host}: {e}")
            finally:
                if local_proxy:
                    await local_proxy.stop()
            await asyncio.sleep(0.5)
        return results

    async def run_test_cycle(self):
        """Execute a full test cycle and save results."""
        logger.info("Starting scheduled test cycle")
        start_time = datetime.now()
        try:
            results = await run_merger(self.settings, sources_file=self.sources_file)
            if self.settings.testing.enable_advanced_tests:
                results = await self.run_advanced_tests_on_top_nodes(results)

            test_data = {
                "timestamp": start_time.isoformat(),
                "total_tested": len(results),
                "successful": len([r for r in results if r.is_reachable]),
                "failed": len([r for r in results if not r.is_reachable]),
                "nodes": [self._serialize_result(r, start_time.isoformat()) for r in results]
            }
            self.current_results_file.write_text(json.dumps(test_data, indent=2), encoding="utf-8")
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(test_data) + "\n")
            logger.info(f"Test cycle completed: {test_data['successful']} successful, {test_data['failed']} failed")
        except Exception as e:
            logger.error(f"Error during test cycle: {e}", exc_info=True)

    def start(self, interval_hours: int = 2):
        """Start the scheduler with specified interval."""
        self.scheduler.add_job(self.run_test_cycle, trigger=IntervalTrigger(hours=interval_hours), id="test_cycle", replace_existing=True)
        self.scheduler.add_job(self.run_test_cycle, id="initial_test", replace_existing=True)
        self.scheduler.start()
        logger.info(f"Scheduler started with {interval_hours}h interval")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")