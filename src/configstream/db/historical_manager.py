"""Manager for historical performance data."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

@dataclass
class NodeHistory:
    """Historical performance data for a node."""
    config_hash: str
    total_tests: int
    successful_tests: int
    avg_ping_ms: float
    avg_packet_loss: float
    uptime_percent: float
    reliability_score: float
    last_seen: datetime
    first_seen: datetime

class HistoricalManager:
    """Manages historical test data and reliability scores."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def hash_config(self, config: str) -> str:
        """Generate hash for config string."""
        return hashlib.sha256(config.encode()).hexdigest()

    async def initialize(self):
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            schema = Path(__file__).with_name("historical_schema.sql")
            if schema.exists():
                await db.executescript(schema.read_text(encoding="utf-8"))
            await db.commit()

    async def record_test(self, test_data: dict):
        """Record a test result."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO node_tests (
                    config_hash, protocol, ip, port, country_code, city,
                    organization, ping_ms, packet_loss_percent, jitter_ms,
                    download_mbps, upload_mbps, is_blocked, reputation_score,
                    cert_valid, test_success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_data.get("config_hash"),
                test_data.get("protocol"),
                test_data.get("ip"),
                test_data.get("port"),
                test_data.get("country_code"),
                test_data.get("city"),
                test_data.get("organization"),
                test_data.get("ping_ms"),
                test_data.get("packet_loss_percent"),
                test_data.get("jitter_ms"),
                test_data.get("download_mbps"),
                test_data.get("upload_mbps"),
                test_data.get("is_blocked"),
                test_data.get("reputation_score"),
                test_data.get("cert_valid"),
                test_data.get("test_success"),
                test_data.get("error_message")
            ))
            await db.commit()

    async def update_reliability(self, config_hash: str):
        """Update reliability score for a node."""
        async with aiosqlite.connect(self.db_path) as db:
            # Calculate statistics from test history
            cursor = await db.execute("""
                SELECT
                    COUNT(*) as total_tests,
                    SUM(CASE WHEN test_success THEN 1 ELSE 0 END) as successful,
                    AVG(CASE WHEN test_success THEN ping_ms END) as avg_ping,
                    AVG(CASE WHEN test_success THEN packet_loss_percent END) as avg_loss,
                    MIN(test_timestamp) as first_seen,
                    MAX(test_timestamp) as last_seen
                FROM node_tests
                WHERE config_hash = ?
                AND test_timestamp > datetime('now', '-30 days')
            """, (config_hash,))

            row = await cursor.fetchone()

            if row and row[0] > 0:
                total, successful, avg_ping, avg_loss, first, last = row
                uptime = (successful / total) * 100 if total > 0 else 0

                # Calculate reliability score (0-100)
                # Factors: uptime (50%), avg_ping (30%), packet_loss (20%)
                ping_score = max(0, 100 - (avg_ping or 0) / 5) if avg_ping else 50
                loss_score = max(0, 100 - (avg_loss or 0) * 10) if avg_loss else 50

                reliability = (
                    uptime * 0.5 +
                    ping_score * 0.3 +
                    loss_score * 0.2
                )

                # Update reliability table
                await db.execute("""
                    INSERT OR REPLACE INTO node_reliability
                    (config_hash, total_tests, successful_tests, avg_ping_ms,
                     avg_packet_loss, uptime_percent, reliability_score,
                     first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config_hash, total, successful, avg_ping, avg_loss,
                    uptime, reliability, first, last
                ))

                await db.commit()

    async def get_reliable_nodes(
        self,
        min_score: float = 70.0,
        limit: int = 100
    ) -> list[NodeHistory]:
        """Get most reliable nodes."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM node_reliability
                WHERE reliability_score >= ?
                AND last_seen > datetime('now', '-7 days')
                ORDER BY reliability_score DESC
                LIMIT ?
            """, (min_score, limit))

            rows = await cursor.fetchall()

            return [
                NodeHistory(
                    config_hash=row[0],
                    total_tests=row[1],
                    successful_tests=row[2],
                    avg_ping_ms=row[3],
                    avg_packet_loss=row[4],
                    uptime_percent=row[5],
                    reliability_score=row[7],
                    last_seen=datetime.fromisoformat(row[6]),
                    first_seen=datetime.fromisoformat(row[8])
                )
                for row in rows
            ]