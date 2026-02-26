"""SQLite storage for usage poll history.

stores every poll result as one row per usage window. the database
lives in the repo root so it can be version-controlled as a lightweight
backup of usage history.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from brightness_monitor.usage import UsageData

log = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "usage.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    polled_at TEXT NOT NULL,
    window_name TEXT NOT NULL,
    utilization REAL NOT NULL,
    remaining REAL NOT NULL,
    resets_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_polls_polled_at
    ON usage_polls (polled_at);

CREATE INDEX IF NOT EXISTS idx_polls_window_name
    ON usage_polls (window_name);
"""


def initialize_database(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """open (or create) the usage database and ensure schema exists.

    returns a persistent connection for the daemon's lifetime.
    """
    path = db_path or DEFAULT_DB_PATH
    log.info("opening usage database at %(path)s", {"path": path})

    connection = sqlite3.connect(str(path))
    connection.executescript(SCHEMA)
    connection.commit()

    return connection


def record_poll(connection: sqlite3.Connection, usage: UsageData) -> None:
    """insert one row per usage window for the current poll."""
    now = datetime.now(tz=timezone.utc).isoformat()

    rows = [
        (
            now,
            window.name,
            window.utilization,
            100.0 - window.utilization,
            window.resets_at.isoformat() if window.resets_at else None,
        )
        for window in usage.windows
    ]

    connection.executemany(
        "INSERT INTO usage_polls (polled_at, window_name, utilization, remaining, resets_at) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    connection.commit()

    log.debug(
        "recorded %(count)d usage windows at %(time)s",
        {"count": len(rows), "time": now},
    )
