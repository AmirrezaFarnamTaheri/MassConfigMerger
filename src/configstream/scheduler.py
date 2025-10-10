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
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .db.historical_manager import HistoricalManager

if TYPE_CHECKING:
    from .config import Settings
    from .core.types import ConfigResult

logger = logging.getLogger(__name__)


class TestScheduler:
    """Manages periodic testing of VPN configurations.

    This class orchestrates automated VPN testing on a schedule and manages
    the storage of results for the web dashboard.

    Attributes:
        settings: Application settings
        output_dir: Directory where test results are saved
        current_results_file: Path to current results JSON
        history_file: Path to historical results JSONL
        scheduler: APScheduler instance
    """

    def __init__(self, settings: "Settings", output_dir: Path):
        """Initialize the scheduler.

        Args:
            settings: ConfigStream settings object
            output_dir: Directory for storing test results
        """
        self.settings = settings
        self.output_dir = output_dir

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.current_results_file = self.output_dir / "current_results.json"
        self.history_file = self.output_dir / "history.jsonl"

        self.scheduler = BackgroundScheduler()
        self.historical_manager = HistoricalManager(self.settings.output.history_db_file)

        logger.info(f"TestScheduler initialized with output_dir: {self.output_dir}")

    def _serialize_result(self, result: "ConfigResult", timestamp: str) -> dict:
        """Convert a ConfigResult to a JSON-serializable dict."""
        return {
            "config": result.config,
            "protocol": result.protocol,
            "ping_time": result.ping_time,
            "country": result.country or "Unknown",
            "city": "Unknown",  # City data is not available in the current ConfigResult
            "organization": result.isp or "Unknown",
            "host": result.host,
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
    ) -> list[ConfigResult]:
        """Run bandwidth and quality tests on top N nodes."""
        from .testing.bandwidth_tester import BandwidthTester
        from .testing.network_quality import NetworkQualityTester

        top_n = self.settings.testing.advanced_test_top_n
        successful = [r for r in results if r.is_reachable]
        top_nodes = sorted(successful, key=lambda x: x.ping_time or float('inf'))[:top_n]

        logger.info(f"Running advanced tests on top {len(top_nodes)} nodes")

        for i, node in enumerate(top_nodes, 1):
            logger.info(f"[{i}/{len(top_nodes)}] Testing {node.host}:{node.port}")

            if self.settings.testing.test_network_quality:
                try:
                    quality_tester = NetworkQualityTester(test_count=10)
                    quality_result = await quality_tester.test_quality(node.host, node.port)
                    node.packet_loss_percent = quality_result.packet_loss_percent
                    node.jitter_ms = quality_result.jitter_ms
                    node.quality_score = quality_result.quality_score
                    node.network_stable = quality_result.is_stable
                except Exception as e:
                    logger.error(f"Quality test failed for {node.host}: {e}")

            if self.settings.testing.test_bandwidth:
                try:
                    bandwidth_tester = BandwidthTester()
                    bandwidth_result = await bandwidth_tester.test_full()
                    node.download_mbps = bandwidth_result.download_mbps
                    node.upload_mbps = bandwidth_result.upload_mbps
                except Exception as e:
                    logger.error(f"Bandwidth test failed for {node.host}: {e}")

            await asyncio.sleep(0.5)

        return results

    def _run_test_cycle_sync(self):
        """Synchronous wrapper for the async test cycle."""
        logger.info("Starting test cycle via sync wrapper.")
        try:
            asyncio.run(self.run_test_cycle())
        except Exception as e:
            logger.error(f"Error running test cycle in sync wrapper: {e}", exc_info=True)

    async def run_test_cycle(self):
        """Execute a full test cycle and save results."""
        logger.info("=" * 60)
        logger.info("Starting scheduled test cycle")
        logger.info("=" * 60)

        start_time = datetime.now()

        try:
            from .vpn_merger import run_merger

            logger.info("Running VPN merger pipeline...")
            results = await run_merger(self.settings)
            logger.info(f"Pipeline completed. Got {len(results)} results.")

            if self.settings.testing.enable_advanced_tests:
                results = await self.run_advanced_tests_on_top_nodes(results)

            timestamp = start_time.isoformat()

            successful = [r for r in results if r.is_reachable]
            failed = [r for r in results if not r.is_reachable]

            test_data = {
                "timestamp": timestamp,
                "total_tested": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "nodes": [self._serialize_result(r, timestamp) for r in results]
            }

            logger.info(f"Saving current results to {self.current_results_file}")
            self.current_results_file.write_text(json.dumps(test_data, indent=2), encoding="utf-8")

            logger.info(f"Appending to history at {self.history_file}")
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(test_data) + "\n")

            # Record results in the database
            for result in results:
                config_hash = self.historical_manager.hash_config(result.config)
                await self.historical_manager.record_test({
                    "config_hash": config_hash,
                    **self._serialize_result(result, timestamp)
                })
                await self.historical_manager.update_reliability(config_hash)

            duration = (datetime.now() - start_time).total_seconds()
            avg_ping = sum(r.ping_time for r in successful if r.ping_time) / len(successful) if successful else 0

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
        logger.info(f"Starting scheduler with {interval_hours} hour interval")

        self.scheduler.add_job(
            self._run_test_cycle_sync,
            trigger=IntervalTrigger(hours=interval_hours),
            id="test_cycle",
            replace_existing=True,
            name=f"VPN Test Cycle (every {interval_hours}h)"
        )

        logger.info("Scheduling immediate initial test")
        self.scheduler.add_job(
            self._run_test_cycle_sync,
            id="initial_test",
            replace_existing=True,
            name="Initial VPN Test"
        )

        self.scheduler.start()
        logger.info("✓ Scheduler started successfully")

    def stop(self):
        """Stop the scheduler gracefully."""
        if self.scheduler.running:
            logger.info("Stopping scheduler...")
            self.scheduler.shutdown(wait=True)
            logger.info("✓ Scheduler stopped")
        else:
            logger.info("Scheduler was not running")

    def get_next_run_time(self) -> str:
        """Get the next scheduled run time."""
        job = self.scheduler.get_job("test_cycle")
        if job and job.next_run_time:
            return job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
        return "Not scheduled"