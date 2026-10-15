"""Batch notes (optionally with a photo) and the per-batch activity log.

Notes are written by the controller (command 'add_note') so they are audited like every other
write. Photo files are saved by the web process before it queues the command: a phone photo is
downscaled to at most PHOTO_MAX_PX (JPEG) plus a THUMB_PX thumbnail under data/photos, and the
original is not kept (the Pi 3's SD card is small).

The activity log is built from AUDIT_LOG rows that carry a batch_id (migration 0010), one row per
dashboard or MCP command. Automatic changes (heater on/off, schedule steps) are not in it.
"""

from __future__ import annotations

import io
import json
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Any

from fermentd.timefmt import isoformat

PHOTO_MAX_PX = 1600
THUMB_PX = 320
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_TEXT = 2000
PHOTO_NAME = re.compile(r"^b\d+-[0-9a-f]{12}(-t)?\.jpg$")

SOURCES = {"web": "Dashboard", "mcp": "Grok Bot (via MCP)"}

# Commands that count as "something you did to this batch", in plain English.
ACTIVITY_ACTIONS = (
    "start_batch", "end_batch", "set_stage", "set_target_temp", "complete_reminder", "add_gravity",
    "add_tweak", "remove_tweak", "log_tasting", "save_variant", "add_note",
)


class PhotoRejected(ValueError):
    pass


def photo_dir(conn: sqlite3.Connection) -> Path:
    """data/photos next to the database file."""
    row = conn.execute("PRAGMA database_list").fetchone()
    return Path(row[2]).resolve().parent / "photos"


def save_photo(directory: Path, batch_id: int, data: bytes) -> tuple[str, str]:
    """Downscale an uploaded image; returns (photo name, thumbnail name)."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    if not data:
        raise PhotoRejected("The photo was empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise PhotoRejected("That photo is too large (over 20 MB).")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoRejected("That file is not a photo this dashboard can read. Try a JPEG or PNG.") from exc
    img = ImageOps.exif_transpose(img).convert("RGB")
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"b{batch_id}-{secrets.token_hex(6)}"
    big = img.copy()
    big.thumbnail((PHOTO_MAX_PX, PHOTO_MAX_PX))
    big.save(directory / f"{stem}.jpg", "JPEG", quality=82, optimize=True)
    img.thumbnail((THUMB_PX, THUMB_PX))
    img.save(directory / f"{stem}-t.jpg", "JPEG", quality=75, optimize=True)
    return f"{stem}.jpg", f"{stem}-t.jpg"


def cmd_add_note(ctx, actor: str, params: dict, command_id: int | None = None):
    from fermentd.control.commands import _reject

    batch = ctx.conn.execute("SELECT id FROM BATCH WHERE id = ?", (params.get("batch_id"),)).fetchone()
    if batch is None:
        return _reject("NOT_FOUND", "batch was not found")
    text = (params.get("text") or "").strip()
    photo, thumb = params.get("photo") or None, params.get("thumb") or None
    for name in (photo, thumb):
        if name is not None and not PHOTO_NAME.match(name):
            return _reject("INVALID", "bad photo name")
    if not text and not photo:
        return _reject("INVALID", "write a note or add a photo")
    if len(text) > MAX_TEXT:
        return _reject("INVALID", f"notes are limited to {MAX_TEXT} characters")
    cur = ctx.conn.execute(
        "INSERT INTO NOTE (batch_id, ts, actor, text, photo, thumb, command_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (batch["id"], isoformat(ctx.clock.now()), actor, text, photo, thumb, command_id),
    )
    return "done", {"ok": True, "batch_id": batch["id"], "note_id": int(cur.lastrowid), "photo": bool(photo)}


def source_label(actor: str) -> str:
    return SOURCES.get(actor, actor.capitalize())


def notes(conn: sqlite3.Connection, batch_id: int) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM NOTE WHERE batch_id = ? ORDER BY ts DESC, id DESC", (batch_id,)).fetchall()


def _json(text: str | None) -> dict:
    try:
        value = json.loads(text or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _f(value: Any) -> str:
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def describe(conn: sqlite3.Connection, action: str, params: dict, result: dict) -> str:
    from fermentd.control.tweaks import tweak_text
    from fermentd.web.status import stage_label

    if action == "start_batch":
        name = params.get("name") or "this batch"
        size = params.get("batch_size_gal")
        return f"Started “{name}”" + (f" ({_f(size)} gal)" if size else "")
    if action == "end_batch":
        return "Ended the batch"
    if action == "set_stage":
        return f"Moved to the next step: {stage_label(result.get('stage') or params.get('stage') or '?')}"
    if action == "set_target_temp":
        return f"Set the target temperature to {_f(result.get('target_f', params.get('target_f')))} °F"
    if action == "complete_reminder":
        row = conn.execute("SELECT text FROM REMINDER WHERE id = ?", (params.get("reminder_id"),)).fetchone()
        return "Marked a reminder done" + (f": {row['text']}" if row else "")
    if action == "add_gravity":
        return f"Logged a gravity reading of {float(result.get('sg', params.get('sg'))):.3f}"
    if action in ("add_tweak", "remove_tweak"):
        row = conn.execute("SELECT * FROM BATCH_TWEAK WHERE id = ?", (result.get("tweak_id"),)).fetchone()
        what = tweak_text(row) if row else "a recipe change"
        if row is not None and row["kind"] == "note":
            return f"Process note: {what}" if action == "add_tweak" else f"Removed a process note: {what}"
        return f"Recipe change: {what}" if action == "add_tweak" else f"Undid a recipe change: {what}"
    if action == "log_tasting":
        row = conn.execute("SELECT rating, make_again FROM TASTING WHERE id = ?", (result.get("tasting_id"),)).fetchone()
        if row is None:
            return "Logged a tasting"
        again = {1: ", would make again", 0: ", would not make again"}.get(row["make_again"], "")
        return f"Tasted it: {row['rating']}/5{again}"
    if action == "save_variant":
        return f"Saved these changes as your version “{result.get('name') or params.get('name')}”"
    if action == "add_note":
        return "Added a note with a photo" if result.get("photo") else "Added a note"
    return action.replace("_", " ").capitalize()


def activity(conn: sqlite3.Connection, batch_id: int, limit: int | None = None) -> list[dict]:
    """What people did to this batch, newest first: one entry per dashboard / MCP command."""
    marks = ",".join("?" * len(ACTIVITY_ACTIONS))
    sql = (
        "SELECT a.id, a.ts, a.actor, a.action, c.params_json, a.new_value FROM AUDIT_LOG a "
        "LEFT JOIN COMMAND c ON c.id = a.command_id "
        f"WHERE a.batch_id = ? AND a.command_id IS NOT NULL AND a.action IN ({marks}) "
        "AND COALESCE(c.status, 'done') = 'done' AND a.actor NOT IN ('schedule', 'control') "
        "ORDER BY a.ts DESC, a.id DESC"
    )
    args: list[Any] = [batch_id, *ACTIVITY_ACTIONS]
    if limit:
        sql += " LIMIT ?"
        args.append(int(limit))
    out = []
    for row in conn.execute(sql, args):
        result = _json(row["new_value"])
        if result.get("ok") is False:
            continue
        out.append({
            "id": row["id"], "ts": row["ts"], "action": row["action"], "actor": row["actor"],
            "source": source_label(row["actor"]),
            "text": describe(conn, row["action"], _json(row["params_json"]), result),
        })
    return out


def timeline(conn: sqlite3.Connection, batch_id: int, only_notes: bool = False, photo_base: str = "/photos") -> list[dict]:
    """Notes (with photos) mixed with the activity log, newest first. Each note already is its own
    entry, so the matching 'Added a note' activity row is left out."""
    items = []
    for n in notes(conn, batch_id):
        items.append({
            "kind": "note", "ts": n["ts"], "source": source_label(n["actor"]), "text": n["text"],
            "photo_url": f"{photo_base}/{n['photo']}" if n["photo"] else None,
            "thumb_url": f"{photo_base}/{n['thumb']}" if n["thumb"] else None,
        })
    if not only_notes:
        for a in activity(conn, batch_id):
            if a["action"] == "add_note":
                continue
            items.append({"kind": a["action"], "ts": a["ts"], "source": a["source"], "text": a["text"],
                          "photo_url": None, "thumb_url": None})
    items.sort(key=lambda i: i["ts"], reverse=True)
    return items
