# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

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
from .core.types import ConfigResult
from .processing import pipeline
from .vpn_merger import run_merger

logger = logging.getLogger(__name__)


class TestScheduler:
    """Manages periodic testing of VPN configurations."""

    def __init__(self, settings: Settings, output_dir: Path):
        self.settings = settings
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scheduler = AsyncIOScheduler()
        self.current_results_file = self.output_dir / "current_results.json"
        self.history_file = self.output_dir / "history.jsonl"

    def _serialize_result(self, result: ConfigResult, timestamp: str) -> dict:
        """Convert a ConfigResult to a JSON-serializable dict."""
        return {
            "config": result.config,
            "protocol": result.protocol,
            "ping_ms": result.ping_time,
            "country": result.country or "Unknown",
            "city": "" if not result.country else result.country,
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
            "network_stable": result.network_stable,
        }

    async def run_advanced_tests_on_top_nodes(
        self,
        results: list[ConfigResult],
        top_n: int = 10
    ) -> list[ConfigResult]:
        """Run bandwidth and quality tests on top N nodes.

        Args:
            results: All test results
            top_n: Number of top nodes to test further

        Returns:
            Updated results with advanced metrics
        """
        from .testing.bandwidth_tester import BandwidthTester
        from .testing.network_quality import NetworkQualityTester

        # Get top N successful nodes by ping
        successful = [r for r in results if r.ping_time > 0]
        top_nodes = sorted(successful, key=lambda x: x.ping_time)[:top_n]

        logger.info(f"Running advanced tests on top {len(top_nodes)} nodes")

        for i, node in enumerate(top_nodes, 1):
            logger.info(f"[{i}/{len(top_nodes)}] Testing {node.host}:{node.port}")

            # Network quality test
            try:
                quality_tester = NetworkQualityTester(test_count=10)
                quality_result = await quality_tester.test_quality(
                    node.host,
                    node.port
                )

                node.packet_loss_percent = quality_result.packet_loss_percent
                node.jitter_ms = quality_result.jitter_ms
                node.quality_score = quality_result.quality_score
                node.network_stable = quality_result.is_stable

            except Exception as e:
                logger.error(f"Quality test failed for {node.host}: {e}")

            # Bandwidth test (optional, can be slow)
            if self.settings.testing.test_bandwidth:
                try:
                    bandwidth_tester = BandwidthTester()
                    bandwidth_result = await bandwidth_tester.test_full()

                    node.download_mbps = bandwidth_result.download_mbps
                    node.upload_mbps = bandwidth_result.upload_mbps
                except Exception as e:
                    logger.error(f"Bandwidth test failed for {node.host}: {e}")

            # Small delay between nodes
            await asyncio.sleep(0.5)

        return results

    async def run_test_cycle(self):
        """Execute a full test cycle and save results."""
        logger.info("=" * 60)
        logger.info("Starting scheduled test cycle")
        logger.info("=" * 60)
        start_time = datetime.now()

        try:
            # Run the merger pipeline
            results = await run_merger(self.settings, self.settings.sources.sources_file)

            # NEW: Run advanced tests on top nodes
            if self.settings.testing.enable_advanced_tests:
                results = await self.run_advanced_tests_on_top_nodes(results, self.settings.testing.advanced_test_top_n)

            # Process results
            timestamp = start_time.isoformat()

            # Count successful and failed tests
            successful = [r for r in results if r.ping_time > 0]
            failed = [r for r in results if r.ping_time < 0]

            # Prepare data for storage
            test_data = {
                "timestamp": timestamp,
                "total_tested": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "nodes": [
                    self._serialize_result(r, timestamp)
                    for r in results
                ]
            }

            # Save current results (overwrite)
            self.current_results_file.write_text(
                json.dumps(test_data, indent=2),
                encoding="utf-8"
            )

            # Append to history (for historical tracking)
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(test_data) + "\n")

            duration = (datetime.now() - start_time).total_seconds()
            avg_ping = sum(r.ping_time for r in successful) / len(successful) if successful else 0

            logger.info("=" * 60)
            logger.info("Test cycle completed successfully!")
            logger.info(f"  Duration: {duration:.2f} seconds")
            logger.info(f"  Total nodes: {len(results)}")
            logger.info(f"  Successful: {len(successful)}")
            logger.info(f"  Failed: {len(failed)}")
            logger.info(f"  Avg ping: {avg_ping:.2f} ms")
            logger.info("=" * 60)

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"Error during test cycle: {e}", exc_info=True)
            logger.error("=" * 60)

    def start(self, interval_hours: int = 2):
        """Start the scheduler with specified interval."""
        self.scheduler.add_job(
            self.run_test_cycle,
            trigger=IntervalTrigger(hours=interval_hours),
            id="test_cycle",
            replace_existing=True
        )

        # Run immediately on start
        self.scheduler.add_job(
            self.run_test_cycle,
            id="initial_test",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(f"Scheduler started with {interval_hours}h interval")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")