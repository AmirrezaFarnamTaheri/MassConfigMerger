# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Main daemon for running scheduled tests and web dashboard."""
from __future__ import annotations

import logging
import signal
import sys
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
        self.running = False

    def start(self, interval_hours: int = 2, web_port: int = 8080):
        """Start the daemon with scheduler and web server."""
        logger.info("Starting ConfigStream Daemon")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Start scheduler
        self.scheduler.start(interval_hours)
        self.running = True

        # Start web dashboard (blocking)
        logger.info(f"Starting web dashboard on port {web_port}")
        run_dashboard(port=web_port)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.scheduler.stop()
        self.running = False
        sys.exit(0)

def main():
    """Entry point for daemon."""
    settings = Settings()
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)

    daemon = ConfigStreamDaemon(settings, data_dir)
    daemon.start(interval_hours=2, web_port=8080)

if __name__ == "__main__":
    main()