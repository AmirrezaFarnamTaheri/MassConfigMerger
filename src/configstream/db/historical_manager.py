"""Manager for historical performance data and reliability tracking.

This module handles all database operations for storing and analyzing
historical VPN node performance data.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

import aiosqlite

logger = logging.getLogger(__name__)


@dataclass
class NodeHistory:
    """Historical performance data for a node.

    Attributes:
        config_hash: Unique hash of the configuration
        total_tests: Total number of tests performed
        successful_tests: Number of successful tests
        failed_tests: Number of failed tests
        avg_ping_ms: Average ping time
        uptime_percent: Percentage of successful tests
        reliability_score: Overall reliability score (0-100)
        stability_score: Network stability score (0-100)
        last_seen: Last time node was tested
        first_seen: First time node was seen
    """
    config_hash: str
    total_tests: int
    successful_tests: int
    failed_tests: int
    avg_ping_ms: float
    avg_packet_loss: float
    avg_jitter: float
    avg_quality_score: float
    uptime_percent: float
    reliability_score: float
    stability_score: float
    last_seen: datetime
    first_seen: datetime
    protocol: str
    ip: str
    port: int
    country_code: str


class HistoricalManager:
    """Manages historical test data and reliability calculations.

    This class provides methods to:
    - Store test results in database
    - Calculate reliability metrics
    - Query historical performance
    - Generate performance summaries

    Example:
        >>> manager = HistoricalManager(Path("data/history.db"))
        >>> await manager.initialize()
        >>> await manager.record_test(test_data)
        >>> reliable = await manager.get_reliable_nodes(min_score=80)
    """

    def __init__(self, db_path: Path):
        """Initialize historical manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def hash_config(self, config: str) -> str:
        """Generate consistent hash for configuration string.

        Args:
            config: Raw configuration string

        Returns:
            SHA256 hash of configuration
        """
        return hashlib.sha256(config.encode('utf-8')).hexdigest()

    async def initialize(self):
        """Initialize database schema.

        Creates tables if they don't exist.
        """
        schema_file = Path(__file__).parent / "historical_schema.sql"

        async with aiosqlite.connect(self.db_path) as db:
            if schema_file.exists():
                schema_sql = schema_file.read_text()
                await db.executescript(schema_sql)
            await db.commit()

        logger.info(f"Database initialized at {self.db_path}")

    async def record_test(self, test_data: Dict[str, Any]):
        """Record a single test result.

        Args:
            test_data: Dictionary with all test data
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO node_test_history (
                    config_hash, protocol, ip, port, country_code, city,
                    organization, ping_ms, test_success, packet_loss_percent,
                    jitter_ms, quality_score, network_stable, download_mbps,
                    upload_mbps, is_blocked, reputation_score, cert_valid,
                    cert_days_until_expiry, is_tor, is_proxy, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_data.get("config_hash"),
                test_data.get("protocol"),
                test_data.get("ip"),
                test_data.get("port"),
                test_data.get("country_code"),
                test_data.get("city"),
                test_data.get("organization"),
                test_data.get("ping_ms"),
                test_data.get("test_success"),
                test_data.get("packet_loss_percent", 0.0),
                test_data.get("jitter_ms", 0.0),
                test_data.get("quality_score", 0.0),
                test_data.get("network_stable", False),
                test_data.get("download_mbps", 0.0),
                test_data.get("upload_mbps", 0.0),
                test_data.get("is_blocked", False),
                test_data.get("reputation_score"),
                test_data.get("cert_valid", True),
                test_data.get("cert_days_until_expiry", 0),
                test_data.get("is_tor", False),
                test_data.get("is_proxy", False),
                test_data.get("error_message")
            ))
            await db.commit()

    async def update_reliability(
        self,
        config_hash: str,
        days_to_analyze: int = 30
    ):
        """Update reliability metrics for a node.

        Args:
            config_hash: Configuration hash
            days_to_analyze: Number of days of history to analyze
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_analyze)

        async with aiosqlite.connect(self.db_path) as db:
            # Calculate statistics from test history
            cursor = await db.execute("""
                SELECT
                    COUNT(*) as total_tests,
                    SUM(CASE WHEN test_success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN test_success = 0 THEN 1 ELSE 0 END) as failed,
                    AVG(CASE WHEN test_success = 1 THEN ping_ms END) as avg_ping,
                    MIN(CASE WHEN test_success = 1 THEN ping_ms END) as min_ping,
                    MAX(CASE WHEN test_success = 1 THEN ping_ms END) as max_ping,
                    AVG(CASE WHEN test_success = 1 THEN packet_loss_percent END) as avg_loss,
                    AVG(CASE WHEN test_success = 1 THEN jitter_ms END) as avg_jitter,
                    AVG(CASE WHEN test_success = 1 THEN quality_score END) as avg_quality,
                    AVG(CASE WHEN test_success = 1 THEN download_mbps END) as avg_download,
                    AVG(CASE WHEN test_success = 1 THEN upload_mbps END) as avg_upload,
                    MIN(test_timestamp) as first_seen,
                    MAX(test_timestamp) as last_seen,
                    MAX(CASE WHEN test_success = 1 THEN test_timestamp END) as last_success
                FROM node_test_history
                WHERE config_hash = ?
                AND test_timestamp > ?
            """, (config_hash, cutoff_date.isoformat()))

            row = await cursor.fetchone()

            if row and row[0] > 0:
                (total, successful, failed, avg_ping, min_ping, max_ping,
                 avg_loss, avg_jitter, avg_quality, avg_download, avg_upload,
                 first, last, last_success) = row

                # Calculate uptime percentage
                uptime = (successful / total * 100) if total > 0 else 0

                # Calculate reliability score (0-100)
                # Factors:
                # - Uptime (40% weight)
                # - Ping quality (30% weight)
                # - Network quality (30% weight)

                ping_score = max(0, 100 - (avg_ping or 0) / 5) if avg_ping else 50
                quality_score = avg_quality or 50

                reliability = (
                    uptime * 0.4 +
                    ping_score * 0.3 +
                    quality_score * 0.3
                )

                # Calculate stability score based on jitter and packet loss
                jitter_score = max(0, 100 - (avg_jitter or 0) * 2)
                loss_score = max(0, 100 - (avg_loss or 0) * 10)
                stability = (jitter_score + loss_score) / 2

                # Get latest node info
                cursor = await db.execute("""
                    SELECT protocol, ip, port, country_code, city
                    FROM node_test_history
                    WHERE config_hash = ?
                    ORDER BY test_timestamp DESC
                    LIMIT 1
                """, (config_hash,))

                node_info = await cursor.fetchone()
                protocol, ip, port, country, city = node_info if node_info else (None,) * 5

                # Update or insert reliability record
                await db.execute("""
                    INSERT OR REPLACE INTO node_reliability (
                        config_hash, total_tests, successful_tests, failed_tests,
                        avg_ping_ms, min_ping_ms, max_ping_ms, avg_packet_loss,
                        avg_jitter, avg_quality_score, avg_download_mbps, avg_upload_mbps,
                        uptime_percent, reliability_score, stability_score,
                        first_seen, last_seen, last_successful_test,
                        protocol, ip, port, country_code, city
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config_hash, total, successful, failed,
                    avg_ping, min_ping, max_ping, avg_loss,
                    avg_jitter, avg_quality, avg_download, avg_upload,
                    uptime, reliability, stability,
                    first, last, last_success,
                    protocol, ip, port, country, city
                ))

                await db.commit()

                logger.debug(
                    f"Updated reliability for {config_hash[:8]}: "
                    f"score={reliability:.1f}, uptime={uptime:.1f}%"
                )

    async def get_reliable_nodes(
        self,
        min_score: float = 70.0,
        limit: int = 100,
        days_active: int = 7
    ) -> List[NodeHistory]:
        """Get most reliable nodes based on historical data.

        Args:
            min_score: Minimum reliability score (0-100)
            limit: Maximum number of nodes to return
            days_active: Only include nodes seen in last N days

        Returns:
            List of NodeHistory objects sorted by reliability
        """
        cutoff_date = datetime.now() - timedelta(days=days_active)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT *
                FROM node_reliability
                WHERE reliability_score >= ?
                AND last_seen > ?
                AND total_tests >= 3
                ORDER BY reliability_score DESC, uptime_percent DESC
                LIMIT ?
            """, (min_score, cutoff_date.isoformat(), limit))

            rows = await cursor.fetchall()

            return [
                NodeHistory(
                    config_hash=row['config_hash'],
                    total_tests=row['total_tests'],
                    successful_tests=row['successful_tests'],
                    failed_tests=row['failed_tests'],
                    avg_ping_ms=row['avg_ping_ms'] or 0.0,
                    avg_packet_loss=row['avg_packet_loss'] or 0.0,
                    avg_jitter=row['avg_jitter'] or 0.0,
                    avg_quality_score=row['avg_quality_score'] or 0.0,
                    uptime_percent=row['uptime_percent'] or 0.0,
                    reliability_score=row['reliability_score'] or 0.0,
                    stability_score=row['stability_score'] or 0.0,
                    last_seen=datetime.fromisoformat(row['last_seen']),
                    first_seen=datetime.fromisoformat(row['first_seen']),
                    protocol=row['protocol'] or '',
                    ip=row['ip'] or '',
                    port=row['port'] or 0,
                    country_code=row['country_code'] or ''
                )
                for row in rows
            ]

    async def get_node_history(
        self,
        config_hash: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get test history for a specific node.

        Args:
            config_hash: Configuration hash
            days: Number of days of history

        Returns:
            List of test result dictionaries
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT *
                FROM node_test_history
                WHERE config_hash = ?
                AND test_timestamp > ?
                ORDER BY test_timestamp DESC
            """, (config_hash, cutoff_date.isoformat()))

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]