"""Automated testing scheduler for periodic VPN node testing."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import Settings
from .vpn_merger import run_merger

logger = logging.getLogger(__name__)

class AppScheduler:
    """Manages periodic testing of VPN configurations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.scheduler = BackgroundScheduler()
        self.current_results_file = self.settings.output.current_results_file
        self.history_file = self.settings.output.history_file

        # Ensure the data directory exists
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def run_test_cycle(self):
        """Synchronous wrapper to run the async test cycle."""
        logger.info("Scheduler triggered. Running test cycle in asyncio event loop.")
        try:
            asyncio.run(self._async_run_test_cycle())
        except Exception as e:
            logger.error(f"An error occurred in the scheduler's test cycle runner: {e}", exc_info=True)

    async def _async_run_test_cycle(self):
        """Execute a full test cycle and save results."""
        logger.info("Starting scheduled test cycle")
        start_time = datetime.now()

        try:
            # Run the merger pipeline using keyword arguments for clarity and robustness
            sources_path = Path(self.settings.sources.sources_file)
            results = await run_merger(cfg=self.settings, sources_file=sources_path, resume_file=None)

            # Prepare data for storage
            test_data = {
                "timestamp": start_time.isoformat(),
                "total_tested": len(results),
                "successful": len([r for r in results if r.ping_time is not None and r.ping_time > 0]),
                "failed": len([r for r in results if r.ping_time is None or r.ping_time <= 0]),
                "nodes": [
                    {
                        "config": r.config,
                        "protocol": r.protocol,
                        "ping_ms": int(r.ping_time * 1000) if r.ping_time and r.ping_time > 0 else -1,
                        "country": r.country or "Unknown",
                        "city": "Unknown",  # TODO: Add city data when available in ConfigResult
                        "organization": r.isp or "Unknown",
                        "ip": r.host,
                        "port": r.port,
                        "is_blocked": r.is_blocked,
                        "timestamp": start_time.isoformat()
                    }
                    for r in results
                ]
            }

            # Save current results (overwrite)
            current_results_json = json.dumps(test_data, indent=2)
            self.current_results_file.write_text(current_results_json, encoding="utf-8")

            # Append to history using a robust read-then-write pattern
            logger.info(
                "Attempting to write to history file at absolute path: %s",
                self.history_file.resolve()
            )
            history_content = ""
            if self.history_file.exists():
                history_content = self.history_file.read_text(encoding="utf-8")

            history_content += json.dumps(test_data) + "\n"
            self.history_file.write_text(history_content, encoding="utf-8")

            logger.info(
                "Test cycle completed: %s successful, %s failed",
                test_data['successful'],
                test_data['failed']
            )

        except Exception as e:
            logger.error("Error during test cycle: %s", e, exc_info=True)

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
        logger.info("Scheduler started with %sh interval", interval_hours)

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
