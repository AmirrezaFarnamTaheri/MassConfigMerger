"""Main daemon for running scheduled tests and web dashboard."""
from __future__ import annotations

import logging
import signal
import sys

from .config import Settings
from .scheduler import AppScheduler
from .web import create_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigStreamDaemon:
    """Main daemon managing scheduler and web dashboard."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.scheduler = AppScheduler(settings)

    def start(self, interval_hours: int = 2, web_port: int = 8080, web_host: str = "127.0.0.1"):
        """Start the daemon with scheduler and web server."""
        logger.info("Starting ConfigStream Daemon")

        # Start the scheduler. It will run in the background.
        self.scheduler.start(interval_hours)

        # Setup signal handlers for a clean exit
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Create and run web dashboard (this is a blocking call)
        logger.info(f"Starting web dashboard on http://{web_host}:{web_port}")
        app = create_app(self.settings)
        app.run(host=web_host, port=web_port, debug=False, use_reloader=False)

    def stop(self):
        """Stops the scheduler."""
        logger.info("Shutting down scheduler...")
        if self.scheduler and self.scheduler.scheduler.running:
            self.scheduler.stop()
        logger.info("Scheduler shut down.")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
        sys.exit(0)


def main():
    """Entry point for daemon."""
    settings = Settings()
    daemon = ConfigStreamDaemon(settings)
    daemon.start()


if __name__ == "__main__":
    main()
