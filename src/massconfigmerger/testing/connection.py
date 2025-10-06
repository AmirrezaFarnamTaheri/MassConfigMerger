from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional


class ConnectionTester:
    """A utility for testing TCP connections."""

    def __init__(self, connect_timeout: float):
        self.connect_timeout = connect_timeout

    async def test(self, ip: str, port: int) -> Optional[float]:
        """Test a TCP connection to a given IP and port, returning the latency."""
        start_time = time.time()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=self.connect_timeout,
            )
            writer.close()
            await writer.wait_closed()
            return time.time() - start_time
        except (OSError, asyncio.TimeoutError) as exc:
            logging.debug("Connection test failed for %s:%d: %s", ip, port, exc)
            return None