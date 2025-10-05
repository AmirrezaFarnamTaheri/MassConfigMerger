from __future__ import annotations

import aiosqlite
import asyncio
from pathlib import Path
from typing import Dict, Optional

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
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

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def get_proxy_history(self) -> Dict[str, Dict[str, int]]:
        if not self.conn:
            await self.connect()

        cursor = await self.conn.execute("SELECT key, successes, failures, last_tested FROM proxy_history")
        rows = await cursor.fetchall()
        history = {}
        for row in rows:
            history[row[0]] = {
                "successes": row[1],
                "failures": row[2],
                "last_tested": row[3],
            }
        return history

    async def update_proxy_history(self, key: str, success: bool):
        if not self.conn:
            await self.connect()

        cursor = await self.conn.execute("SELECT successes, failures FROM proxy_history WHERE key = ?", (key,))
        row = await cursor.fetchone()

        if row:
            successes, failures = row
            if success:
                successes += 1
            else:
                failures += 1
            await self.conn.execute(
                "UPDATE proxy_history SET successes = ?, failures = ?, last_tested = strftime('%s', 'now') WHERE key = ?",
                (successes, failures, key),
            )
        else:
            await self.conn.execute(
                "INSERT INTO proxy_history (key, successes, failures, last_tested) VALUES (?, ?, ?, strftime('%s', 'now'))",
                (key, 1 if success else 0, 1 if not success else 0),
            )
        await self.conn.commit()