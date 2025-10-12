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
import os
import threading
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import Settings
from .db.historical_manager import HistoricalManager
from .vpn_merger import run_merger

logger = logging.getLogger(__name__)

_history_lock = threading.Lock()

class TestScheduler:
    """Manages periodic testing of VPN configurations."""

    def __init__(self, settings: Settings, output_dir: Path):
        self.settings = settings
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scheduler = BackgroundScheduler(daemon=True)
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
            results = await run_merger(self.settings, Path(self.settings.sources.sources_file))

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
            with _history_lock:
                with open(self.history_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(test_data) + "\n")
                    f.flush()
                    os.fsync(f.fileno())

            logger.info(f"Test cycle completed: {test_data['successful']} successful, "
                       f"{test_data['failed']} failed")

        except Exception as e:
            logger.error(f"Error during test cycle: {e}", exc_info=True)

    def _run_test_cycle_sync(self):
        """Synchronous wrapper to run the async test cycle."""
        logger.info("Scheduler triggered. Running async test cycle in a new event loop.")
        try:
            asyncio.run(self.run_test_cycle())
        except Exception as e:
            logger.error(f"Exception in scheduled task: {e}", exc_info=True)

    def start(self, interval_hours: int = 2):
        """Start the scheduler with specified interval."""
        logger.info(f"Scheduling test cycle to run every {interval_hours} hours.")
        self.scheduler.add_job(
            self._run_test_cycle_sync,
            trigger=IntervalTrigger(hours=interval_hours),
            id="test_cycle",
            name="Periodic VPN Test Cycle",
            replace_existing=True
        )

        # Run immediately on start in a separate thread to not block
        logger.info("Scheduling immediate initial test run.")
        initial_run_thread = threading.Thread(target=self._run_test_cycle_sync, daemon=True)
        initial_run_thread.start()

        self.scheduler.start()
        logger.info("Scheduler started.")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            logger.info("Shutting down scheduler.")
            self.scheduler.shutdown()
            logger.info("Scheduler stopped.")
        else:
            logger.info("Scheduler was not running.")
