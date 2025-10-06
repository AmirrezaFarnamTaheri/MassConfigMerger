from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import aiosqlite


class Database:
    """A class to manage the SQLite database for proxy history."""

    def __init__(self, db_path: Path):
        """Initialize the Database."""
        self.db_path = db_path.resolve()
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Establish a connection to the database and create tables if they don't exist."""
        if not self.db_path.parent.is_dir():
            raise ValueError(f"Database directory not found: {self.db_path.parent}")
        self.conn = await aiosqlite.connect(self.db_path)
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS proxy_history (
                key TEXT PRIMARY KEY,
                successes INTEGER NOT NULL DEFAULT 0,
                failures INTEGER NOT NULL DEFAULT 0,
                last_tested INTEGER
            )
            """
        )
        await self.conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def _ensure_connected(self) -> None:
        """Ensure the database connection is active."""
        if not self.conn:
            await self.connect()

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a SQL query with parameters."""
        await self._ensure_connected()
        return await self.conn.execute(sql, params)

    async def executemany(self, sql: str, params: list) -> aiosqlite.Cursor:
        """Execute a SQL query for many parameter sets."""
        await self._ensure_connected()
        return await self.conn.executemany(sql, params)

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self.conn:
            await self.conn.commit()

    async def get_proxy_history(self) -> Dict[str, Dict[str, int]]:
        """Fetch the entire proxy history from the database."""
        cursor = await self.execute("SELECT key, successes, failures, last_tested FROM proxy_history")
        rows = await cursor.fetchall()
        return {
            row[0]: {"successes": row[1], "failures": row[2], "last_tested": row[3]}
            for row in rows
        }

    async def record_proxy(self, key: str, success: bool) -> None:
        """Record a single proxy test result."""
        if success:
            sql = """
                INSERT INTO proxy_history (key, successes, failures, last_tested)
                VALUES (?, 1, 0, strftime('%s', 'now'))
                ON CONFLICT(key) DO UPDATE SET
                    successes = successes + 1,
                    last_tested = strftime('%s', 'now');
            """
        else:
            sql = """
                INSERT INTO proxy_history (key, successes, failures, last_tested)
                VALUES (?, 0, 1, strftime('%s', 'now'))
                ON CONFLICT(key) DO UPDATE SET
                    failures = failures + 1,
                    last_tested = strftime('%s', 'now');
            """
        await self.execute(sql, (key,))
        await self.commit()

    async def add_proxy_history_batch(self, batch: List[tuple[str, bool]]):
        """Update proxy history in a batch."""
        tasks = [self.record_proxy(key, success) for key, success in batch]
        await asyncio.gather(*tasks)

    async def prune_old_records(self, days: int) -> int:
        """Prune records that have not been tested in a given number of days."""
        threshold = days * 86400  # Convert days to seconds
        sql = "DELETE FROM proxy_history WHERE (strftime('%s', 'now') - last_tested) > ?"
        cursor = await self.execute(sql, (threshold,))
        await self.commit()
        return cursor.rowcount