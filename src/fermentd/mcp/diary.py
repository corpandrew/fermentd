"""MCP tools for batch notes (with photo links) and the per-batch activity log."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from fermentd.control import notes as nt
from fermentd.mcp import queries as q
from fermentd.mcp.writes import Writer, WriteRejected

DEFAULT_DASHBOARD_URL = "http://127.0.0.1:8080"
ENV_FILE = Path("config/fermentd.env")


def dashboard_url() -> str:
    """Base for photo links: $FERMENTD_DASHBOARD_URL, then config/fermentd.env, then localhost."""
    value = os.environ.get("FERMENTD_DASHBOARD_URL")
    if not value and ENV_FILE.is_file():
        for line in ENV_FILE.read_text().splitlines():
            key, sep, raw = line.strip().partition("=")
            if sep and key.strip() == "FERMENTD_DASHBOARD_URL":
                value = raw.strip().strip("'\"")
    return (value or DEFAULT_DASHBOARD_URL).rstrip("/")


def _note(n: sqlite3.Row) -> dict:
    base = dashboard_url()
    return {
        "note_id": n["id"], "text": n["text"], "at": q.when(n["ts"]), "source": nt.source_label(n["actor"]),
        "photo_url": f"{base}/photos/{n['photo']}" if n["photo"] else None,
        "thumbnail_url": f"{base}/photos/{n['thumb']}" if n["thumb"] else None,
    }


def list_batch_notes(ro: sqlite3.Connection, batch_id: int) -> dict:
    batch = q._batch_row(ro, batch_id)
    rows = [_note(n) for n in nt.notes(ro, batch_id)]
    return {"batch_id": batch_id, "name": batch["name"], "notes": rows, "count": len(rows),
            "order": "newest first",
            "photos": "Photo links open on the dashboard (on your private network). Photos are added from the dashboard."}


def add_batch_note(ro: sqlite3.Connection, writer: Writer, batch_id: int, text: str) -> dict:
    q._batch_row(ro, batch_id)
    text = (text or "").strip()
    if not text:
        raise WriteRejected("note text is empty")
    if len(text) > nt.MAX_TEXT:
        raise WriteRejected(f"notes are limited to {nt.MAX_TEXT} characters")
    res = writer.submit("add_note", {"batch_id": batch_id, "text": text})
    row = writer.conn.execute("SELECT * FROM NOTE WHERE id = ?", (res["note_id"],)).fetchone()
    return {"added": _note(row), "batch_id": batch_id}


def get_batch_activity(ro: sqlite3.Connection, batch_id: int, limit: int | None = 50) -> dict:
    batch = q._batch_row(ro, batch_id)
    limit = max(1, min(int(limit or 50), 500))
    items = nt.activity(ro, batch_id, limit)
    return {
        "batch_id": batch_id, "name": batch["name"],
        "activity": [{"what": a["text"], "action": a["action"], "at": q.when(a["ts"]), "source": a["source"]}
                     for a in items],
        "order": "newest first", "limit": limit,
        "note": "Things people did to this batch from the dashboard or Grok Bot. Automatic heat mat switching "
                "and alerts are not included (see list_alerts).",
    }
