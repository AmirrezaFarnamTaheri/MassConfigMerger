from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import aiosqlite

from configstream.db import Database


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture to create a temporary database path using a real temporary directory."""
    return tmp_path / "proxy_history.db"


@pytest.mark.asyncio
async def test_db_connect_and_close(db_path: Path):
    """Test that the database can be connected to and closed."""
    db = Database(db_path)
    await db.connect()
    assert db.conn is not None

    # Verify connection is open by executing a simple query
    await db.conn.execute("SELECT 1")

    await db.close()

    # After closing, the connection object becomes unusable.
    # Trying to use it should raise a ValueError.
    with pytest.raises(ValueError, match="no active connection"):
        await db.conn.execute("SELECT 1")


@pytest.mark.asyncio
async def test_db_connect_no_directory():
    """Test that a ValueError is raised if the database directory does not exist."""
    db_path = Path("/nonexistent/directory/proxy_history.db")
    db = Database(db_path)
    with pytest.raises(ValueError, match="Database directory not found"):
        await db.connect()


@pytest.mark.asyncio
async def test_db_get_proxy_history(db_path: Path):
    """Test retrieving proxy history from the database."""
    db = Database(db_path)
    await db.connect()

    # Add some data to the database
    await db.conn.execute("INSERT INTO proxy_history (key, successes, failures, last_tested) VALUES (?, ?, ?, ?)", ("test_key", 10, 2, 12345))
    await db.conn.commit()

    history = await db.get_proxy_history()
    assert "test_key" in history
    assert history["test_key"]["successes"] == 10
    assert history["test_key"]["failures"] == 2
    assert history["test_key"]["last_tested"] == 12345

    await db.close()


@pytest.mark.asyncio
async def test_get_proxy_history_auto_connect(db_path: Path):
    """Test that get_proxy_history automatically connects to the database."""
    db = Database(db_path)
    assert db.conn is None
    await db.get_proxy_history()
    assert db.conn is not None
    await db.close()


@pytest.mark.asyncio
async def test_add_proxy_history_batch(db_path: Path):
    """Test updating proxy history with a batch of results."""
    db = Database(db_path)
    await db.connect()

    batch = [
        ("success_key", True),
        ("failure_key", False),
        ("success_key", True),  # Test duplicate key
    ]
    await db.add_proxy_history_batch(batch)

    history = await db.get_proxy_history()
    assert "success_key" in history
    assert history["success_key"]["successes"] == 2
    assert history["success_key"]["failures"] == 0

    assert "failure_key" in history
    assert history["failure_key"]["successes"] == 0
    assert history["failure_key"]["failures"] == 1

    await db.close()


@pytest.mark.asyncio
async def test_add_proxy_history_batch_auto_connect(db_path: Path):
    """Test that add_proxy_history_batch automatically connects to the database."""
    db = Database(db_path)
    assert db.conn is None
    await db.add_proxy_history_batch([("test_key", True)])
    assert db.conn is not None
    await db.close()
