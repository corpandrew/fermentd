"""Profile detail and 'what's next' for the MCP tools (read-only)."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime

from fermentd.mcp import queries as q
from fermentd.web.status import _NEXT_ACTION, _STAGE

_CORE = {
    "prep": "Getting ready: brew, mix or prepare the must.",
    "making": "Making it: brewing or mixing before fermentation starts. No temperature control yet.",
    "primary": "Primary fermentation: yeast is turning sugar into alcohol and CO2.",
    "secondary": "Secondary: clearing and finishing after the main ferment.",
    "packaging": "Packaging: bottling or transferring.",
    "conditioning": "Conditioning: carbonating or maturing in the bottle or vessel.",
    "done": "Done: chilled, served or stored. The batch can be ended.",
}


def current_profile_ids() -> set[str]:
    from fermentd.profiles.loader import load_profiles

    try:
        return set(load_profiles())
    except Exception:  # noqa: BLE001
        return set()


def _latest_profile(ro: sqlite3.Connection, profile_id: str) -> tuple[sqlite3.Row, dict]:
    row = ro.execute(
        "SELECT * FROM BEVERAGE_PROFILE WHERE id = ? ORDER BY version DESC LIMIT 1", (profile_id,)
    ).fetchone()
    if row is None:
        raise q.NotFound(f"unknown profile_id {profile_id!r}; see list_profiles")
    return row, json.loads(row["definition_json"])


def _guide(profile: dict, size: str) -> dict | None:
    from fermentd.web.markdown import load_guide

    try:
        return load_guide(profile.get("recipe"), size=size)
    except Exception:  # noqa: BLE001
        return None


def _sections(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    parts = re.split(r"^##\s+(.*)$", body, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        text = re.sub(r"\[\[([^|\]]*)\|([^\]]*)\]\]", r"\1", parts[i + 1]).strip()
        out[parts[i].strip()] = text
    return out


def _raw_body(profile: dict) -> str:
    from fermentd.web.markdown import apply_size, find_recipe

    path = find_recipe(profile.get("recipe"))
    if path is None:
        return ""
    text = path.read_text()
    end = text.find("\n---\n", 4)
    return text[end + 5 :] if end > 0 else ""


def _sized_sections(profile: dict, half: bool) -> dict[str, str]:
    from fermentd.web.markdown import apply_size

    return _sections(apply_size(_raw_body(profile), half))


def stage_label(stage_id: str) -> str:
    return _STAGE.get(stage_id, stage_id.replace("_", " ").capitalize())


def _steps_by_stage(meta: dict, stage_ids: list[str] | None = None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for step in (meta or {}).get("steps", []) or []:
        out.setdefault(step.get("profile_stage") or step.get("stage") or "", []).append(step.get("text", ""))
    # The Prep stage ("Making it") shows the brewing / mixing steps: the guide's steps for the first
    # stage after Prep, since the recipes list making and bottling day together.
    if stage_ids and "prep" in stage_ids and "prep" not in out:
        later = [s for s in stage_ids if s != "prep" and out.get(s)]
        if later:
            out["prep"] = list(out[later[0]])
    return out


def get_profile(ro: sqlite3.Connection, profile_id: str) -> dict:
    row, d = _latest_profile(ro, profile_id)
    full = _guide(d, "1")
    half = _guide(d, "0.5")
    meta = (full or {}).get("meta", {})
    half_meta = (half or {}).get("meta", {}) if half and half.get("size") == "0.5" else None
    steps = _steps_by_stage(meta, [s["id"] for s in d.get("stages", [])])
    stages = []
    for s in d.get("stages", []):
        stages.append(
            {
                "id": s["id"],
                "label": stage_label(s["id"]),
                "core": s.get("core"),
                "meaning": _CORE["making"] if s["id"] == "prep" else _CORE.get(s.get("core"), ""),
                "target_f": s.get("target_f"),
                "temp_step": s.get("ramp"),
                "steps": steps.get(s["id"], []),
            }
        )
    timeline = {
        k: meta.get(k)
        for k in (
            "carbonation_window_h", "chill_before_open_h", "drink_within_days", "primary_days", "ferment_days",
            "condition_days", "aging_weeks", "aging_months", "lager_weeks",
        )
        if meta.get(k) is not None
    }
    return {
        "profile_id": profile_id,
        "name": d.get("name"),
        "drink_type": d.get("category"),
        "drink_type_label": (full or {}).get("category_label"),
        "status": row["status"],
        "description": (d.get("guidance") or {}).get("note") or meta.get("description") or meta.get("style"),
        "vessel_types": d.get("vessel_types") or "any",
        "temperature": d.get("temperature"),
        "stages": stages,
        "default_stage": d.get("default_stage"),
        "reminders_template": d.get("reminders", []),
        "guidance": d.get("guidance"),
        "safety_cutoff_f": (d.get("safety") or {}).get("cutoff_f"),
        "batch_sizes_gal": (full or {}).get("sizes", ["1"]),
        "yield_1gal": meta.get("yield"),
        "yield_half_gal": None if half_meta is None else half_meta.get("yield"),
        "ingredients_1gal": meta.get("ingredients", []),
        "ingredients_half_gal": None if half_meta is None else half_meta.get("ingredients"),
        "equipment": meta.get("equipment", []),
        "timeline": timeline,
        "guide_sections_1gal": _sized_sections(d, False) if full else {},
        "guide_available": full is not None,
    }


def _advance_trigger(profile: dict, steps: dict[str, list[str]], current: str, nxt: str | None) -> str | None:
    if nxt is None:
        return None
    # Prefer a step or reminder that says when to move on ("When ... ", "If ... rock hard").
    candidates = steps.get(nxt, []) + [r.get("text", "") for r in profile.get("reminders", [])
                                       if r.get("at", "").startswith(f"stage:{current}+")]
    for text in candidates:
        if re.match(r"^(When|Once|After|If)\b", text.strip()):
            return text.strip()
    action = _NEXT_ACTION.get(nxt)
    return f"{action} when the current stage's steps are complete." if action else None


def next_actions(ro: sqlite3.Connection, batch_id: int | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    if batch_id is None:
        rows = ro.execute("SELECT * FROM BATCH WHERE ended_at IS NULL ORDER BY id").fetchall()
    else:
        rows = [q._batch_row(ro, batch_id)]
    out = []
    for batch in rows:
        profile = q._profile(batch)
        ids = [s["id"] for s in profile.get("stages", [])]
        cur = batch["stage"]
        spec = next((s for s in profile.get("stages", []) if s["id"] == cur), {})
        nxt = ids[ids.index(cur) + 1] if cur in ids and ids.index(cur) + 1 < len(ids) else None
        guide = _guide(profile, "0.5" if (batch["volume_l"] or 3.785) < 2.5 else "1")
        steps = _steps_by_stage((guide or {}).get("meta", {}), ids)
        reminders = []
        for r in ro.execute(
            "SELECT * FROM REMINDER WHERE batch_id = ? AND status IN ('pending', 'open') ORDER BY due_at", (batch["id"],)
        ):
            due = q.parse_iso(r["due_at"])
            reminders.append(
                {
                    "reminder_id": r["id"],
                    "key": r["reminder_key"],
                    "text": r["text"],
                    "due": q.when(r["due_at"]),
                    "overdue": due <= now,
                    "repeats_every_s": r["repeat_seconds"],
                    "status": r["status"],
                }
            )
        out.append(
            {
                "batch_id": batch["id"],
                "name": batch["name"],
                "vessel_id": batch["vessel_id"],
                "status": "active" if batch["ended_at"] is None else "ended",
                "stage": cur,
                "stage_label": stage_label(cur),
                "stage_meaning": _CORE["making"] if cur == "prep" else _CORE.get(spec.get("core"), ""),
                "stage_started": q.when(batch["stage_started_at"]),
                "next_steps": steps.get(cur, []),
                "pending_reminders": reminders,
                "overdue_count": sum(1 for r in reminders if r["overdue"]),
                "next_stage": nxt,
                "next_stage_label": None if nxt is None else stage_label(nxt),
                "advance_when": _advance_trigger(profile, steps, cur, nxt),
                "upcoming_steps_next_stage": [] if nxt is None else steps.get(nxt, []),
                "safety": (profile.get("guidance") or {}).get("safety_glass") or None,
            }
        )
    return {"as_of": q.when(q._iso(now)), "batches": out}
