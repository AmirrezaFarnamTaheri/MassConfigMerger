"""Main daemon for running scheduled tests and web dashboard."""
from __future__ import annotations

import asyncio
import logging
import signal
import threading
from pathlib import Path

from .config import Settings
from .scheduler import TestScheduler
from .web_dashboard import run_dashboard

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigStreamDaemon:
    """Main daemon managing scheduler and web dashboard."""

    def __init__(self, settings: Settings, data_dir: Path):
        self.settings = settings
        self.data_dir = data_dir
        self.scheduler = TestScheduler(settings, data_dir)
        self.shutdown_event = asyncio.Event()

    async def start(self, interval_hours: int = 2, web_port: int = 8080):
        """Start the daemon with scheduler and web server."""
        logger.info("Starting ConfigStream Daemon")

        # Start scheduler
        self.scheduler.start(interval_hours)

        # Start web dashboard
        web_task = asyncio.create_task(run_dashboard(port=web_port))

        logger.info(f"Web dashboard scheduled to run on port {web_port}")

        await self.shutdown_event.wait()

        # Cleanup
        web_task.cancel()
        self.scheduler.stop()
        logger.info("Daemon has been shut down.")

    def _signal_handler(self):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received, initiating graceful shutdown...")
        self.shutdown_event.set()

def main():
    """Entry point for daemon."""
    settings = Settings()
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)

    daemon = ConfigStreamDaemon(settings, data_dir)

    loop = asyncio.get_event_loop()

    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, daemon._signal_handler)
            except Exception as exc:
                logger.warning(f"Could not set signal handlers: {exc}")

    try:
        loop.run_until_complete(daemon.start(interval_hours=2, web_port=8080))
    finally:
        loop.close()

if __name__ == "__main__":
    main()