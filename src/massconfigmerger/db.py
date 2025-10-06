from __future__ import annotations

import aiosqlite
from pathlib import Path
from typing import Dict, Optional

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path.resolve()
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
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
        await self.conn.execute(sql, (key,))
        await self.conn.commit()

# End of file
