import sqlite3
from pathlib import Path

from fermentd.db.connection import connect
from fermentd.db.migrate import migrate


def test_migrate_enables_wal_and_is_idempotent(tmp_path: Path):
    conn = connect(tmp_path / "fermentd.db")
    first = migrate(conn)
    second = migrate(conn)
    assert first == [
        "0001_init.sql",
        "0002_notification_outbox.sql",
        "0003_vessels_and_user_profiles.sql",
        "0004_dashboard_overrides.sql",
        "0005_stage_started.sql",
        "0006_scale.sql",
        "0007_target_reached.sql",
        "0008_slowing_notified.sql",
        "0009_tweaks_tastings.sql",
        "0010_notes_activity.sql",
    ]
    assert second == []
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    for name in (
        "TEMP_ZONE",
        "VESSEL",
        "BATCH",
        "BEVERAGE_PROFILE",
        "READING",
        "READING_HOURLY",
        "GRAVITY_READING",
        "BASELINE_SEGMENT",
        "DIGEST_LOG",
        "ALERT",
        "REMINDER",
        "COMMAND",
        "AUDIT_LOG",
        "API_KEY",
        "NOTIFICATION_OUTBOX",
    ):
        assert name in tables


def test_command_idempotency_is_unique_per_actor(tmp_path: Path):
    conn = connect(tmp_path / "fermentd.db")
    migrate(conn)
    conn.execute(
        """
        INSERT INTO COMMAND (
            idempotency_key, actor, type, params_json, status, created_at, expires_at
        ) VALUES ('k', 'web', 'heaters_off', '{}', 'pending', '2026-10-12T00:00:00Z', '2026-10-12T00:01:00Z')
        """
    )
    try:
        conn.execute(
            """
            INSERT INTO COMMAND (
                idempotency_key, actor, type, params_json, status, created_at, expires_at
            ) VALUES ('k', 'web', 'heaters_off', '{}', 'pending', '2026-10-12T00:00:00Z', '2026-10-12T00:01:00Z')
            """
        )
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised
