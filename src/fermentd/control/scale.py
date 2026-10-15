"""Scale sampling, tare/calibration commands, and the activity alerts. Runs in the controller,
which is the only process that touches GPIO."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

from fermentd.drivers.base import ScaleUnavailable
from fermentd.timefmt import isoformat

if TYPE_CHECKING:
    from fermentd.control.commands import CommandContext

MIN_CAL_WEIGHT_G = 100.0
MIN_COUNTS_PER_GRAM = 0.5  # an HX711 at gain 128 with a 10 kg cell gives roughly 100-450 counts/g


def sync_scale_rows(conn: sqlite3.Connection, config) -> None:
    for vessel in config.vessels:
        scale = vessel.scale
        if scale is None or scale.driver == "none":
            continue
        conn.execute(
            """
            INSERT INTO SCALE (vessel_id, driver, tare_offset, counts_per_gram, status)
            VALUES (?, ?, ?, ?, 'unknown')
            ON CONFLICT(vessel_id) DO UPDATE SET
                driver = excluded.driver,
                tare_offset = COALESCE(SCALE.tare_offset, excluded.tare_offset),
                counts_per_gram = COALESCE(SCALE.counts_per_gram, excluded.counts_per_gram)
            """,
            (vessel.id, scale.driver, scale.tare_offset, scale.counts_per_gram),
        )


def _set_status(conn: sqlite3.Connection, vessel_id: str, status: str, detail: str | None, ts: str, raw=None) -> None:
    conn.execute(
        "UPDATE SCALE SET status = ?, status_detail = ?, status_at = ?, last_raw = COALESCE(?, last_raw) "
        "WHERE vessel_id = ?",
        (status, detail, ts, raw, vessel_id),
    )


def grams_from_raw(row: sqlite3.Row, raw: float) -> float | None:
    if row["tare_offset"] is None or not row["counts_per_gram"]:
        return None
    return (raw - row["tare_offset"]) / row["counts_per_gram"]


def sample_scales(service: Any) -> None:
    """One median-filtered reading per scale every sample_interval_s. A missing or unwired
    scale only sets status 'not_connected'; it never stops temperature control."""
    now_mono = service.clock.monotonic()
    ts = isoformat(service.clock.now())
    due_at = service.runtime.scale_due
    for vessel in service.config.vessels:
        sensor = service.hardware.scales.get(vessel.id)
        if sensor is None or vessel.scale is None:
            continue
        if now_mono < due_at.get(vessel.id, float("-inf")):
            continue
        due_at[vessel.id] = now_mono + vessel.scale.sample_interval_s
        try:
            raw = sensor.read_raw()
        except ScaleUnavailable as exc:
            _set_status(service.conn, vessel.id, "not_connected", str(exc), ts)
            continue
        except Exception as exc:  # never let a scale take the control loop down
            _set_status(service.conn, vessel.id, "not_connected", f"read error: {exc}", ts)
            continue
        row = service.conn.execute("SELECT * FROM SCALE WHERE vessel_id = ?", (vessel.id,)).fetchone()
        grams = grams_from_raw(row, raw)
        status = "ok" if grams is not None else ("needs_tare" if row["tare_offset"] is None else "needs_calibration")
        _set_status(service.conn, vessel.id, status, None, ts, raw)
        batch = service.conn.execute(
            "SELECT id FROM BATCH WHERE vessel_id = ? AND ended_at IS NULL", (vessel.id,)
        ).fetchone()
        service.conn.execute(
            "INSERT OR IGNORE INTO WEIGHT_READING (ts, vessel_id, batch_id, raw, grams) VALUES (?, ?, ?, ?, ?)",
            (ts, vessel.id, None if batch is None else batch["id"], raw, grams),
        )
        if batch is not None and grams is not None:
            if (
                service.conn.execute("SELECT start_weight_g FROM BATCH WHERE id = ?", (batch["id"],)).fetchone()[
                    "start_weight_g"
                ]
                is None
            ):
                service.conn.execute("UPDATE BATCH SET start_weight_g = ? WHERE id = ?", (grams, batch["id"]))
            check_activity(service, vessel.id, batch["id"])


def check_activity(service: Any, vessel_id: str, batch_id: int) -> None:
    from fermentd.control.weight import weight_summary

    summary = weight_summary(service.conn, batch_id)
    if summary is None:
        return
    state = summary.get("state")
    _maybe_slowing(service, vessel_id, batch_id, summary)
    if state == "stable":
        service._raise(
            vessel_id,
            vessel_id,
            batch_id,
            "fermentation_quiet",
            "action",
            {"text": summary["text"] + " Take a hydrometer reading."},
        )


def _maybe_slowing(service: Any, vessel_id: str, batch_id: int, summary: dict) -> None:
    """Once per batch: the CO2 loss rate has fallen below slowing_fraction of a meaningful peak."""
    cfg = service.config.control
    rate, peak = summary.get("rate_g_day"), summary.get("peak_g_day")
    if rate is None or not peak or peak < cfg.slowing_min_peak_g_day or rate >= peak * cfg.slowing_fraction:
        return
    row = service.conn.execute(
        "SELECT name, slowing_notified_at FROM BATCH WHERE id = ?", (batch_id,)
    ).fetchone()
    if row is None or row["slowing_notified_at"] is not None:
        return
    ts = isoformat(service.clock.now())
    service.conn.execute("UPDATE BATCH SET slowing_notified_at = ? WHERE id = ?", (ts, batch_id))
    body = (
        f"{row['name']}: fermentation has slowed to {rate:.1f} g/day of CO2, down from a peak of "
        f"{peak:.0f} g/day. Take a hydrometer reading; if it holds steady over a few days it is ready "
        "to bottle (or to prime and bottle for sparkling)."
    )
    service.conn.execute(
        "INSERT INTO EVENT (ts, type, severity, actor, detail_json) VALUES (?, 'fermentation_slowing', 'info', 'control', ?)",
        (ts, json.dumps({"batch_id": batch_id, "rate_g_day": rate, "peak_g_day": peak, "text": body})),
    )
    service.notifier.notify("fermentation_slowing", "info", f"{row['name']}: slowing down", body)


# ---- commands (executed by the controller; the web and CLI only enqueue them) ----


def _sensor_and_row(ctx: CommandContext, params: dict):
    from fermentd.control.commands import _reject

    vessel_id = str(params.get("vessel_id") or "")
    sensor = (ctx.scales or {}).get(vessel_id)
    row = ctx.conn.execute("SELECT * FROM SCALE WHERE vessel_id = ?", (vessel_id,)).fetchone()
    if sensor is None or row is None:
        return _reject("NO_SCALE", "This vessel has no scale enabled in fermentd.yaml.")
    try:
        raw = sensor.read_raw()
    except ScaleUnavailable as exc:
        _set_status(ctx.conn, vessel_id, "not_connected", str(exc), isoformat(ctx.clock.now()))
        return _reject("SCALE_NOT_CONNECTED", f"Scale not connected: {exc}")
    return vessel_id, row, raw


def scale_read(ctx: CommandContext, actor: str, params: dict):
    got = _sensor_and_row(ctx, params)
    if got[0] == "rejected":
        return got
    vessel_id, row, raw = got
    grams = grams_from_raw(row, raw)
    return "done", {"ok": True, "vessel_id": vessel_id, "raw": raw, "grams": grams}


def scale_tare(ctx: CommandContext, actor: str, params: dict):
    got = _sensor_and_row(ctx, params)
    if got[0] == "rejected":
        return got
    vessel_id, _row, raw = got
    now = isoformat(ctx.clock.now())
    ctx.conn.execute("UPDATE SCALE SET tare_offset = ?, tared_at = ? WHERE vessel_id = ?", (raw, now, vessel_id))
    _set_status(ctx.conn, vessel_id, "needs_calibration", None, now, raw)
    row = ctx.conn.execute("SELECT * FROM SCALE WHERE vessel_id = ?", (vessel_id,)).fetchone()
    if row["counts_per_gram"]:
        _set_status(ctx.conn, vessel_id, "ok", None, now, raw)
    return "done", {"ok": True, "vessel_id": vessel_id, "tare_offset": raw}


def scale_calibrate(ctx: CommandContext, actor: str, params: dict):
    from fermentd.control.commands import _reject

    try:
        known = float(params.get("grams"))
    except (TypeError, ValueError):
        return _reject("OUT_OF_RANGE", "Enter the known weight in grams, for example 1000.")
    if not (MIN_CAL_WEIGHT_G <= known <= 10_000):
        return _reject("OUT_OF_RANGE", "Use a known weight between 100 g and 10,000 g (1 L of water = 1000 g).")
    got = _sensor_and_row(ctx, params)
    if got[0] == "rejected":
        return got
    vessel_id, row, raw = got
    if row["tare_offset"] is None:
        return _reject("NEEDS_TARE", "Tare the empty platform first.")
    cpg = (raw - row["tare_offset"]) / known
    if abs(cpg) < MIN_COUNTS_PER_GRAM:
        return _reject(
            "NO_CHANGE",
            "The reading barely changed with the weight on. Check the weight is on the platform and the wiring.",
        )
    now = isoformat(ctx.clock.now())
    ctx.conn.execute(
        "UPDATE SCALE SET counts_per_gram = ?, cal_weight_g = ?, calibrated_at = ? WHERE vessel_id = ?",
        (cpg, known, now, vessel_id),
    )
    _set_status(ctx.conn, vessel_id, "ok", None, now, raw)
    return "done", {"ok": True, "vessel_id": vessel_id, "counts_per_gram": cpg}
