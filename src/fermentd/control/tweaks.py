"""Recipe tweaks, tasting log and "my version" variants: commands (run by the controller) and the
read helpers shared by the web pages and the MCP tools."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from fermentd.timefmt import isoformat, parse_iso

KINDS = ("change", "add", "remove", "note")
# Which taste sliders make sense per drink type, with plain-English labels.
_SLIDERS = {
    "soda": [("carbonation", "Fizz", "flat", "very fizzy"), ("sweetness", "Sweetness", "not sweet", "very sweet"),
             ("flavor", "Ginger / flavor kick", "mild", "strong")],
    "ginger_beer": [("carbonation", "Fizz", "flat", "very fizzy"), ("sweetness", "Sweetness", "not sweet", "very sweet"),
                    ("flavor", "Ginger heat", "mild", "fiery")],
    "cider": [("dryness", "Dryness", "sweet", "bone dry"), ("carbonation", "Sparkle", "still", "very sparkling"),
              ("flavor", "Apple flavor", "light", "intense")],
    "keeved_cider": [("sweetness", "Sweetness", "dry", "very sweet"), ("carbonation", "Sparkle", "still", "very sparkling"),
                     ("flavor", "Apple flavor", "light", "intense")],
    "wine": [("dryness", "Dryness", "sweet", "bone dry"), ("flavor", "Fruit / body", "light", "full")],
    "sparkling_wine": [("dryness", "Dryness", "sweet", "brut"), ("carbonation", "Bubbles", "gentle", "lively"),
                       ("flavor", "Toasty / fruit", "light", "rich")],
    "ale": [("carbonation", "Fizz", "flat", "very fizzy"), ("dryness", "Finish", "malty / sweet", "dry"),
            ("flavor", "Hop / flavor strength", "mild", "bold")],
    "lager": [("carbonation", "Fizz", "flat", "very fizzy"), ("dryness", "Finish", "malty", "crisp"),
              ("flavor", "Flavor strength", "mild", "bold")],
    "kombucha": [("carbonation", "Fizz", "flat", "very fizzy"), ("sweetness", "Sweet vs sour", "sour", "sweet"),
                 ("flavor", "Flavor strength", "mild", "strong")],
    "water_kefir": [("carbonation", "Fizz", "flat", "very fizzy"), ("sweetness", "Sweetness", "not sweet", "very sweet"),
                    ("flavor", "Flavor strength", "mild", "strong")],
}
_DEFAULT_SLIDERS = [("carbonation", "Fizz", "flat", "very fizzy"), ("sweetness", "Sweetness", "not sweet", "very sweet"),
                    ("dryness", "Dryness", "sweet", "dry"), ("flavor", "Flavor strength", "mild", "strong")]
SLIDER_KEYS = ("carbonation", "sweetness", "dryness", "flavor")


class Invalid(ValueError):
    pass


def sliders_for(category: str | None) -> list[dict]:
    return [{"key": k, "label": label, "low": lo, "high": hi}
            for k, label, lo, hi in _SLIDERS.get(category or "", _DEFAULT_SLIDERS)]


def _profile(batch: sqlite3.Row) -> dict:
    try:
        return json.loads(batch["profile_snapshot_json"] or "{}")
    except ValueError:
        return {}


def base_ingredients(batch: sqlite3.Row) -> list[dict]:
    """Ingredients of the profile's written recipe at this batch's size."""
    from fermentd.web.markdown import load_guide

    half = (batch["volume_l"] or 3.785) < 2.5
    try:
        guide = load_guide(_profile(batch).get("recipe"), size="0.5" if half else "1")
    except Exception:  # noqa: BLE001
        guide = None
    items = (guide or {}).get("meta", {}).get("ingredients", []) or []
    return [{"id": i.get("id") or i.get("item"), "item": i.get("item"), "amount": str(i.get("amount", ""))} for i in items]


# ------------------------------------------------------------------ validation (pure)

def clean_tweak(params: dict, base: list[dict]) -> dict:
    kind = (params.get("kind") or "").strip()
    if kind not in KINDS:
        raise Invalid(f"kind must be one of {', '.join(KINDS)}")
    by_id = {b["id"]: b for b in base}
    by_name = {(b["item"] or "").lower(): b for b in base}
    ing = (params.get("ingredient_id") or params.get("ingredient") or "").strip()
    match = by_id.get(ing) or by_name.get(ing.lower()) if ing else None
    out = {"kind": kind, "ingredient_id": None, "item": None, "from_amount": None, "to_amount": None,
           "note": (params.get("note") or "").strip()[:500] or None}
    if kind == "note":
        if not out["note"]:
            raise Invalid("a process note needs some text, e.g. 'steeped ginger 20 min'")
        return out
    if kind in ("change", "remove"):
        if match is None:
            names = ", ".join(f"{b['id']} ({b['item']})" for b in base) or "none"
            raise Invalid(f"'{ing}' is not in the recipe. Ingredients: {names}")
        out.update(ingredient_id=match["id"], item=match["item"], from_amount=match["amount"])
        if kind == "change":
            to = (params.get("to_amount") or params.get("amount") or "").strip()
            if not to:
                raise Invalid("say the new amount, e.g. '4 oz'")
            out["to_amount"] = to[:60]
        return out
    item = (params.get("item") or ing).strip()
    if not item:
        raise Invalid("name the added ingredient, e.g. 'lime zest'")
    to = (params.get("to_amount") or params.get("amount") or "").strip()
    out.update(item=item[:80], to_amount=to[:60] or None)
    return out


def clean_tasting(params: dict, now_iso: str) -> dict:
    def score(key: str, required: bool = False) -> int | None:
        raw = params.get(key)
        if raw in (None, ""):
            if required:
                raise Invalid(f"{key} (1-5) is required")
            return None
        try:
            value = int(float(raw))
        except (TypeError, ValueError):
            raise Invalid(f"{key} must be a whole number 1-5") from None
        if not 1 <= value <= 5:
            raise Invalid(f"{key} must be 1-5")
        return value

    when = params.get("tasted_at") or params.get("date")
    if when:
        try:
            text = str(when).strip()
            if len(text) == 10:
                text += "T12:00:00"
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                from zoneinfo import ZoneInfo

                dt = dt.replace(tzinfo=ZoneInfo("America/New_York"))
            when = isoformat(dt)
        except ValueError:
            raise Invalid("date must look like 2026-10-20") from None
    again = params.get("make_again")
    if isinstance(again, str):
        again = {"yes": 1, "true": 1, "1": 1, "on": 1, "no": 0, "false": 0, "0": 0, "": None}.get(again.lower(), None)
    elif again is not None:
        again = 1 if again else 0
    return {
        "tasted_at": when or now_iso,
        "rating": score("rating", required=True),
        **{k: score(k) for k in SLIDER_KEYS},
        "notes": (params.get("notes") or "").strip()[:2000] or None,
        "make_again": again,
    }


# ------------------------------------------------------------------ controller commands

def _batch(ctx, params):
    from fermentd.control.commands import _reject

    row = ctx.conn.execute("SELECT * FROM BATCH WHERE id = ?", (params.get("batch_id"),)).fetchone()
    return row if row is not None else _reject("NOT_FOUND", "batch was not found")


def insert_tweak(conn: sqlite3.Connection, batch_id: int, tweak: dict, now: str, actor: str) -> int:
    cur = conn.execute(
        "INSERT INTO BATCH_TWEAK (batch_id, kind, ingredient_id, item, from_amount, to_amount, note, created_at, actor) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (batch_id, tweak["kind"], tweak.get("ingredient_id"), tweak.get("item"), tweak.get("from_amount"),
         tweak.get("to_amount"), tweak.get("note"), now, actor),
    )
    return int(cur.lastrowid)


def cmd_add_tweak(ctx, actor: str, params: dict):
    from fermentd.control.commands import _reject

    batch = _batch(ctx, params)
    if isinstance(batch, tuple):
        return batch
    try:
        tweak = clean_tweak(params, base_ingredients(batch))
    except Invalid as exc:
        return _reject("INVALID", str(exc))
    tid = insert_tweak(ctx.conn, batch["id"], tweak, isoformat(ctx.clock.now()), actor)
    return "done", {"ok": True, "batch_id": batch["id"], "tweak_id": tid}


def cmd_remove_tweak(ctx, actor: str, params: dict):
    from fermentd.control.commands import _reject

    row = ctx.conn.execute("SELECT * FROM BATCH_TWEAK WHERE id = ?", (params.get("tweak_id"),)).fetchone()
    if row is None or row["removed_at"] is not None:
        return _reject("NOT_FOUND", "that change was not found")
    if params.get("batch_id") is not None and int(params["batch_id"]) != row["batch_id"]:
        return _reject("INVALID", f"change {row['id']} belongs to batch {row['batch_id']}")
    ctx.conn.execute("UPDATE BATCH_TWEAK SET removed_at = ? WHERE id = ?", (isoformat(ctx.clock.now()), row["id"]))
    return "done", {"ok": True, "batch_id": row["batch_id"], "tweak_id": row["id"]}


def cmd_log_tasting(ctx, actor: str, params: dict):
    from fermentd.control.commands import _reject

    batch = _batch(ctx, params)
    if isinstance(batch, tuple):
        return batch
    now = isoformat(ctx.clock.now())
    try:
        t = clean_tasting(params, now)
    except Invalid as exc:
        return _reject("INVALID", str(exc))
    cur = ctx.conn.execute(
        "INSERT INTO TASTING (batch_id, tasted_at, rating, carbonation, sweetness, dryness, flavor, notes, make_again, "
        "created_at, actor) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (batch["id"], t["tasted_at"], t["rating"], t["carbonation"], t["sweetness"], t["dryness"], t["flavor"],
         t["notes"], t["make_again"], now, actor),
    )
    return "done", {"ok": True, "batch_id": batch["id"], "tasting_id": int(cur.lastrowid)}


def cmd_save_variant(ctx, actor: str, params: dict):
    from fermentd.control.commands import _reject

    batch = _batch(ctx, params)
    if isinstance(batch, tuple):
        return batch
    tweaks = active_tweaks(ctx.conn, batch["id"])
    if not tweaks:
        return _reject("INVALID", "this batch has no recipe changes to save")
    name = (params.get("name") or "").strip()[:80] or f"My {(_profile(batch).get('name') or batch['profile_id']).lower()}"
    keep = [{k: t[k] for k in ("kind", "ingredient_id", "item", "from_amount", "to_amount", "note")} for t in tweaks]
    cur = ctx.conn.execute(
        "INSERT INTO PROFILE_VARIANT (profile_id, name, tweaks_json, source_batch_id, created_at, actor) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (batch["profile_id"], name, json.dumps(keep), batch["id"], isoformat(ctx.clock.now()), actor),
    )
    return "done", {"ok": True, "batch_id": batch["id"], "variant_id": int(cur.lastrowid), "name": name}


def copy_into_new_batch(ctx, batch_id: int, profile_id: str, params: dict, actor: str):
    """After start_batch: apply a variant's tweaks or copy them from an earlier batch.
    Returns an error message or None. Validated before the batch is created (see check_copy_source)."""
    tweaks, variant_id = _copy_source(ctx.conn, profile_id, params)
    now = isoformat(ctx.clock.now())
    for t in tweaks:
        insert_tweak(ctx.conn, batch_id, t, now, actor)
    if variant_id is not None:
        ctx.conn.execute("UPDATE BATCH SET variant_id = ? WHERE id = ?", (variant_id, batch_id))


def check_copy_source(conn: sqlite3.Connection, profile_id: str, params: dict) -> str | None:
    try:
        _copy_source(conn, profile_id, params)
    except Invalid as exc:
        return str(exc)
    return None


def _copy_source(conn, profile_id: str, params: dict) -> tuple[list[dict], int | None]:
    vid, bid = params.get("variant_id"), params.get("copy_tweaks_from_batch_id")
    if vid not in (None, "") and bid not in (None, ""):
        raise Invalid("use a variant or copy from a batch, not both")
    if vid not in (None, ""):
        row = conn.execute("SELECT * FROM PROFILE_VARIANT WHERE id = ?", (int(vid),)).fetchone()
        if row is None:
            raise Invalid(f"recipe version {vid} was not found")
        if row["profile_id"] != profile_id:
            raise Invalid(f"'{row['name']}' is a version of {row['profile_id']}, not {profile_id}")
        return json.loads(row["tweaks_json"]), int(row["id"])
    if bid not in (None, ""):
        src = conn.execute("SELECT * FROM BATCH WHERE id = ?", (int(bid),)).fetchone()
        if src is None:
            raise Invalid(f"batch {bid} was not found")
        if src["profile_id"] != profile_id:
            raise Invalid(f"batch {bid} used {src['profile_id']}, not {profile_id}")
        return ([{k: t[k] for k in ("kind", "ingredient_id", "item", "from_amount", "to_amount", "note")}
                 for t in active_tweaks(conn, int(bid))], None)
    return [], None


# ------------------------------------------------------------------ reads

def active_tweaks(conn: sqlite3.Connection, batch_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM BATCH_TWEAK WHERE batch_id = ? AND removed_at IS NULL ORDER BY id", (batch_id,)
    ).fetchall()


def tweak_text(t: Any) -> str:
    if t["kind"] == "change":
        return f"{t['item']}: {t['from_amount']} → {t['to_amount']}" + (f" ({t['note']})" if t["note"] else "")
    if t["kind"] == "add":
        return f"Added {t['item']}" + (f", {t['to_amount']}" if t["to_amount"] else "") + (f" ({t['note']})" if t["note"] else "")
    if t["kind"] == "remove":
        return f"Left out {t['item']}" + (f" ({t['note']})" if t["note"] else "")
    return t["note"] or ""


def recipe_view(conn: sqlite3.Connection, batch: sqlite3.Row) -> dict:
    """Base recipe next to this batch's version, with each change marked."""
    tweaks = active_tweaks(conn, batch["id"])
    rows = []
    for b in base_ingredients(batch):
        mine = [t for t in tweaks if t["ingredient_id"] == b["id"] and t["kind"] in ("change", "remove")]
        last = mine[-1] if mine else None
        state = "same" if last is None else ("removed" if last["kind"] == "remove" else "changed")
        rows.append({"id": b["id"], "item": b["item"], "recipe": b["amount"],
                     "mine": "left out" if state == "removed" else (last["to_amount"] if last else b["amount"]),
                     "state": state, "tweak_id": None if last is None else last["id"],
                     "note": None if last is None else last["note"]})
    for t in tweaks:
        if t["kind"] == "add":
            rows.append({"id": None, "item": t["item"], "recipe": "—", "mine": t["to_amount"] or "added",
                         "state": "added", "tweak_id": t["id"], "note": t["note"]})
    notes = [{"tweak_id": t["id"], "text": t["note"], "at": t["created_at"]} for t in tweaks if t["kind"] == "note"]
    variant = None
    if "variant_id" in batch.keys() and batch["variant_id"]:
        v = conn.execute("SELECT id, name FROM PROFILE_VARIANT WHERE id = ?", (batch["variant_id"],)).fetchone()
        variant = None if v is None else {"variant_id": v["id"], "name": v["name"]}
    return {
        "ingredients": rows,
        "notes": notes,
        "changes": [{"tweak_id": t["id"], "kind": t["kind"], "text": tweak_text(t), "at": t["created_at"],
                     "actor": t["actor"]} for t in tweaks],
        "change_count": len(tweaks),
        "variant": variant,
    }


def tastings(conn: sqlite3.Connection, batch_id: int | None = None) -> list[sqlite3.Row]:
    if batch_id is None:
        return conn.execute(
            "SELECT TASTING.*, BATCH.name AS batch_name, BATCH.profile_id FROM TASTING JOIN BATCH ON BATCH.id = TASTING.batch_id "
            "ORDER BY tasted_at DESC, TASTING.id DESC"
        ).fetchall()
    return conn.execute(
        "SELECT TASTING.*, BATCH.name AS batch_name, BATCH.profile_id FROM TASTING JOIN BATCH ON BATCH.id = TASTING.batch_id "
        "WHERE batch_id = ? ORDER BY tasted_at DESC, TASTING.id DESC", (batch_id,)
    ).fetchall()


def ranking(conn: sqlite3.Connection, profile_id: str | None = None, drink_type: str | None = None) -> list[dict]:
    rows = conn.execute(
        """
        SELECT BATCH.*, AVG(TASTING.rating) AS avg_rating, MAX(TASTING.rating) AS best_rating, COUNT(TASTING.id) AS n,
               SUM(CASE WHEN TASTING.make_again = 1 THEN 1 ELSE 0 END) AS again_yes,
               SUM(CASE WHEN TASTING.make_again = 0 THEN 1 ELSE 0 END) AS again_no
        FROM BATCH JOIN TASTING ON TASTING.batch_id = BATCH.id
        GROUP BY BATCH.id
        """
    ).fetchall()
    out = []
    for r in rows:
        profile = _profile(r)
        if profile_id and r["profile_id"] != profile_id:
            continue
        if drink_type and profile.get("category") != drink_type:
            continue
        latest = conn.execute(
            "SELECT notes FROM TASTING WHERE batch_id = ? AND notes IS NOT NULL ORDER BY tasted_at DESC LIMIT 1", (r["id"],)
        ).fetchone()
        out.append({
            "batch_id": r["id"], "name": r["name"], "profile_id": r["profile_id"], "profile_name": profile.get("name"),
            "drink_type": profile.get("category"), "started_at": r["started_at"], "ended_at": r["ended_at"],
            "avg_rating": round(r["avg_rating"], 2), "best_rating": r["best_rating"], "tastings": r["n"],
            "make_again": None if not (r["again_yes"] or r["again_no"]) else r["again_yes"] >= r["again_no"],
            "latest_note": None if latest is None else latest["notes"],
            "changes": [tweak_text(t) for t in active_tweaks(conn, r["id"])],
        })
    out.sort(key=lambda x: (-x["avg_rating"], -x["tastings"], x["started_at"]), reverse=False)
    return out


def variants(conn: sqlite3.Connection, profile_id: str | None = None) -> list[dict]:
    q = "SELECT * FROM PROFILE_VARIANT" + (" WHERE profile_id = ?" if profile_id else "") + " ORDER BY id"
    out = []
    for v in conn.execute(q, (profile_id,) if profile_id else ()):
        tw = json.loads(v["tweaks_json"])
        out.append({"variant_id": v["id"], "profile_id": v["profile_id"], "name": v["name"],
                    "from_batch_id": v["source_batch_id"], "created_at": v["created_at"],
                    "changes": [tweak_text(t) for t in tw]})
    return out


def age_label(ts: str, now: datetime) -> str:
    days = (now - parse_iso(ts)).days
    return "today" if days <= 0 else ("yesterday" if days == 1 else f"{days} days ago")
