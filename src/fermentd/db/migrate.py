"""Apply numbered SQL migrations once."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS = Path(__file__).parent / "migrations"


def migrate(conn: sqlite3.Connection) -> list[str]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
    new: list[str] = []
    for path in sorted(MIGRATIONS.glob("*.sql")):
        if path.name in applied:
            continue
        conn.executescript(path.read_text())
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (path.name, datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
        new.append(path.name)
    conn.commit()
    return new
