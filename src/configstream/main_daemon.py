"""Main daemon for running scheduled tests and web dashboard."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
import threading
import time
from pathlib import Path

from .config import Settings
from .scheduler import TestScheduler
from .web_dashboard import run_dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ConfigStreamDaemon:
    """Main daemon managing scheduler and web dashboard."""

    def __init__(self, settings: Settings, data_dir: Path):
        self.settings = settings
        self.data_dir = data_dir
        self.scheduler = TestScheduler(settings, data_dir)
        self.running = False
        self._dashboard_thread = None

    def start(self, interval_hours: int = 2, web_port: int = 8080):
        """Start the daemon with scheduler and web server."""
        logger.info("Starting ConfigStream Daemon")

        # Setup signal handlers only in main thread
        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            except Exception as exc:
                logger.warning(f"Could not set signal handlers: {exc}")

        # Start scheduler
        self.scheduler.start(interval_hours)
        self.running = True

        # Start web dashboard in a background thread to avoid blocking
        def _run_dashboard():
            try:
                logger.info(f"Starting web dashboard on port {web_port}")
                run_dashboard(port=web_port)
            except Exception as exc:
                logger.error(f"Web dashboard stopped with error: {exc}", exc_info=True)

        self._dashboard_thread = threading.Thread(
            target=_run_dashboard, name="dashboard", daemon=True
        )
        self._dashboard_thread.start()

        # Keep the main thread alive until a shutdown signal is processed
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self._signal_handler(signal.SIGINT, None)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        try:
            self.scheduler.stop()
        finally:
            self.running = False

def main():
    """Entry point for daemon."""
    settings = Settings()
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)

    daemon = ConfigStreamDaemon(settings, data_dir)
    daemon.start(interval_hours=2, web_port=8080)

if __name__ == "__main__":
    main()