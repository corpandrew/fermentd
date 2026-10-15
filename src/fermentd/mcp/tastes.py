"""MCP reads and writes for recipe tweaks, tastings and saved recipe versions."""

from __future__ import annotations

import sqlite3

from fermentd.control import tweaks as tw
from fermentd.mcp import queries as q
from fermentd.mcp.writes import Writer, WriteRejected


def _when_all(d: dict, *keys: str) -> dict:
    for k in keys:
        if k in d:
            d[k] = q.when(d[k])
    return d


def get_batch_tweaks(ro: sqlite3.Connection, batch_id: int) -> dict:
    batch = q._batch_row(ro, batch_id)
    view = tw.recipe_view(ro, batch)
    for c in view["changes"]:
        _when_all(c, "at")
    for n in view["notes"]:
        _when_all(n, "at")
    return {"batch_id": batch_id, "name": batch["name"], "profile_id": batch["profile_id"], **view}


def _tasting(row: sqlite3.Row) -> dict:
    return {
        "tasting_id": row["id"], "batch_id": row["batch_id"], "batch_name": row["batch_name"],
        "profile_id": row["profile_id"], "tasted": q.when(row["tasted_at"]), "rating": row["rating"],
        "carbonation": row["carbonation"], "sweetness": row["sweetness"], "dryness": row["dryness"],
        "flavor": row["flavor"], "notes": row["notes"],
        "make_again": None if row["make_again"] is None else bool(row["make_again"]),
    }


def list_tastings(ro: sqlite3.Connection, batch_id: int | None = None) -> dict:
    if batch_id is not None:
        q._batch_row(ro, batch_id)
    rows = [_tasting(r) for r in tw.tastings(ro, batch_id)]
    return {"batch_id": batch_id, "tastings": rows,
            "scale": "1-5 for rating and every slider; slider meaning depends on the drink type"}


def get_best_batches(ro: sqlite3.Connection, profile_id: str | None = None, drink_type: str | None = None,
                     limit: int = 10) -> dict:
    ranked = tw.ranking(ro, profile_id, drink_type)[: max(1, min(int(limit), 50))]
    for r in ranked:
        _when_all(r, "started_at", "ended_at")
    return {"profile_id": profile_id, "drink_type": drink_type, "ranked": ranked,
            "note": "Ranked by average tasting rating; 'changes' are that batch's recipe tweaks."}


def list_variants(ro: sqlite3.Connection, profile_id: str | None = None) -> dict:
    out = tw.variants(ro, profile_id)
    for v in out:
        _when_all(v, "created_at")
    return {"variants": out}


def add_batch_tweak(ro, writer: Writer, batch_id: int, kind: str, ingredient: str | None = None,
                    amount: str | None = None, item: str | None = None, note: str | None = None) -> dict:
    batch = q._batch_row(ro, batch_id)
    try:
        tw.clean_tweak({"kind": kind, "ingredient": ingredient, "to_amount": amount, "item": item, "note": note},
                       tw.base_ingredients(batch))
    except tw.Invalid as exc:
        raise WriteRejected(str(exc)) from None
    res = writer.submit("add_tweak", {"batch_id": batch_id, "kind": kind, "ingredient": ingredient,
                                      "to_amount": amount, "item": item, "note": note})
    out = get_batch_tweaks(writer.conn, batch_id)
    out["added_tweak_id"] = res["tweak_id"]
    return out


def remove_batch_tweak(ro, writer: Writer, tweak_id: int, batch_id: int | None = None) -> dict:
    row = ro.execute("SELECT * FROM BATCH_TWEAK WHERE id = ?", (tweak_id,)).fetchone()
    if row is None or row["removed_at"] is not None:
        raise WriteRejected(f"change {tweak_id} was not found (or was already removed)")
    if batch_id is not None and row["batch_id"] != batch_id:
        raise WriteRejected(f"change {tweak_id} belongs to batch {row['batch_id']}, not {batch_id}")
    writer.submit("remove_tweak", {"tweak_id": tweak_id, "batch_id": row["batch_id"]})
    return get_batch_tweaks(writer.conn, row["batch_id"])


def log_tasting(ro, writer: Writer, batch_id: int, rating: int, date: str | None = None,
                carbonation: int | None = None, sweetness: int | None = None, dryness: int | None = None,
                flavor: int | None = None, notes: str | None = None, make_again: bool | None = None) -> dict:
    q._batch_row(ro, batch_id)
    params = {"batch_id": batch_id, "rating": rating, "tasted_at": date, "carbonation": carbonation,
              "sweetness": sweetness, "dryness": dryness, "flavor": flavor, "notes": notes,
              "make_again": make_again}
    try:
        tw.clean_tasting(params, "2000-01-01T00:00:00Z")
    except tw.Invalid as exc:
        raise WriteRejected(str(exc)) from None
    res = writer.submit("log_tasting", params)
    out = list_tastings(writer.conn, batch_id)
    out["added_tasting_id"] = res["tasting_id"]
    return out


def save_tweaks_as_variant(ro, writer: Writer, batch_id: int, name: str | None = None) -> dict:
    q._batch_row(ro, batch_id)
    if not tw.active_tweaks(ro, batch_id):
        raise WriteRejected(f"batch {batch_id} has no recipe changes to save")
    res = writer.submit("save_variant", {"batch_id": batch_id, "name": name or ""})
    return next(v for v in list_variants(writer.conn)["variants"] if v["variant_id"] == res["variant_id"])
