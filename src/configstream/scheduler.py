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

logger = logging.getLogger(__name__)


class TestScheduler:
    """Manages periodic testing of VPN configurations."""

    def __init__(self, settings: Settings, output_dir: Path | None = None):
        self.settings = settings
        self.output_dir = output_dir or Path("./data")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scheduler = AsyncIOScheduler()
        self.current_results_file = self.output_dir / "current_results.json"
        self.history_file = self.output_dir / "history.jsonl"

    async def run_test_cycle(self):
        """Execute a full test cycle and save results."""
        logger.info("Starting scheduled test cycle")
        start_time = datetime.now()

        try:
            # Run the merger pipeline
            sources_file = Path(self.settings.sources.sources_file)
            results = await run_merger(self.settings, sources_file=sources_file, resume_file=None)

            # Resolve hosts to IPs with caching
            host_ip_cache: dict[str, str | None] = {}

            async def resolve_ip(host: str | None) -> str | None:
                if not host:
                    return None
                if host in host_ip_cache:
                    return host_ip_cache[host]
                try:
                    loop = asyncio.get_running_loop()
                    ip = await loop.getaddrinfo(host, None)
                    # Extract first IPv4/IPv6 textual address
                    resolved = ip[0][4][0] if ip else None
                except Exception:
                    resolved = None
                host_ip_cache[host] = resolved
                return resolved

            nodes = []
            for r in results:
                ping_ms = int(r.ping_time * 1000) if (r.ping_time is not None and r.ping_time > 0) else -1
                ip_val = await resolve_ip(r.host)
                nodes.append({
                    "config": r.config,
                    "protocol": r.protocol,
                    "ping_ms": ping_ms,
                    "country": r.country or "Unknown",
                    "city": "Unknown",
                    "organization": r.isp or "Unknown",
                    "ip": ip_val or (r.host or ""),
                    "port": r.port,
                    "is_blocked": r.is_blocked,
                    "timestamp": start_time.isoformat()
                })

            test_data = {
                "timestamp": start_time.isoformat(),
                "total_tested": len(results),
                "successful": len([r for r in results if r.ping_time is not None and r.ping_time > 0]),
                "failed": len([r for r in results if r.ping_time is None or r.ping_time <= 0]),
                "nodes": nodes
            }

            # Save current results (atomic overwrite)
            tmp_file = self.current_results_file.with_suffix(".json.tmp")
            tmp_file.write_text(json.dumps(test_data, indent=2), encoding="utf-8")
            tmp_file.replace(self.current_results_file)

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