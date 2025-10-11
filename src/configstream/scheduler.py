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
from .db.historical_manager import HistoricalManager
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
        self.db_manager = HistoricalManager(self.output_dir / "history.db")

    async def run_test_cycle(self):
        """Execute a full test cycle and save results."""
        logger.info("Starting scheduled test cycle")
        start_time = datetime.now()

        try:
            # Initialize DB if not already done
            await self.db_manager.initialize()

            # Run the merger pipeline
            results = await run_merger(self.settings)

            # Prepare data for storage
            test_data = {
                "timestamp": start_time.isoformat(),
                "total_tested": len(results),
                "successful": len([r for r in results if r.ping_time > 0]),
                "failed": len([r for r in results if r.ping_time < 0]),
                "nodes": [],
            }

            for r in results:
                node_data = {
                    "config": r.config,
                    "protocol": r.protocol,
                    "ping_ms": r.ping_time,
                    "country_code": r.country or "Unknown",
                    "test_success": r.is_reachable,
                    "is_blocked": r.is_blocked,
                    "timestamp": start_time.isoformat(),
                    "ip": r.host,
                    "port": r.port,
                    "city": r.country,
                    "organization": r.isp,
                    "config_hash": self.db_manager.hash_config(r.config),
                }
                test_data["nodes"].append(node_data)
                await self.db_manager.record_test(node_data)
                await self.db_manager.update_reliability(node_data["config_hash"])


            # Save current results (overwrite)
            self.current_results_file.write_text(
                json.dumps(test_data, indent=2),
                encoding="utf-8"
            )

            # Append to history (for historical tracking)
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(test_data) + "\n")

            logger.info(f"Test cycle completed: {test_data['successful']} successful, "
                       f"{test_data['failed']} failed")

        except Exception as e:
            logger.error(f"Error during test cycle: {e}", exc_info=True)

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