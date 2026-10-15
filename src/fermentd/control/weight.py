"""Weight-based fermentation tracking from the load-cell samples.

Assumptions (also shown on the dashboard):
- Every gram the vessel loses is CO2 leaving through the airlock. Evaporation through an airlock
  is a gram or two a week, so it is ignored.
- A sudden drop of more than STEP_G between two samples is a hydrometer sample, a top-up or the
  jug being moved, not fermentation. It is cut out by re-basing at that point.
- ABV ≈ CO2 lost (g) / volume (L) / 7.9. Pure stoichiometry (C6H12O6 → 2 C2H5OH + 2 CO2:
  1.05 g ethanol per g CO2, 0.789 g/mL) gives /7.5; 7.9 is the usual home-brew factor that also
  allows for sugar going to yeast growth. About 1.5-2 g/L of CO2 stays dissolved in the liquid
  at fermentation temperatures, so early on the estimate runs a little low.
- Gravity drop ≈ ABV / 131.25 (the same formula as the hydrometer ABV, run backwards).
"""

from __future__ import annotations

import json
import sqlite3
import statistics
from datetime import datetime

from fermentd.timefmt import parse_iso

ABV_FACTOR = 7.9
STEP_G = 30.0
STABLE_WINDOW_S = 48 * 3600
STABLE_BAND_G = 3.0
MIN_ACTIVITY_G = 5.0
SLOWING_FRACTION = 0.2
GAL_L = 3.785


def batch_volume_l(conn: sqlite3.Connection, batch: sqlite3.Row) -> tuple[float, str]:
    if batch["volume_l"]:
        return float(batch["volume_l"]), "batch volume"
    try:
        recipe = json.loads(batch["recipe_json"] or "{}")
    except ValueError:
        recipe = {}
    gal = (recipe.get("yield") or {}).get("volume_gal")
    if gal:
        return float(gal) * GAL_L, "recipe batch size"
    row = conn.execute("SELECT capacity_l FROM VESSEL WHERE id = ?", (batch["vessel_id"],)).fetchone()
    if row is not None and row["capacity_l"]:
        return float(row["capacity_l"]), "vessel capacity"
    return GAL_L, "assumed 1 gallon"


def fermentation_loss(points: list[tuple[datetime, float]]) -> tuple[float, list[tuple[datetime, float]]]:
    """Cumulative fermentation loss (g) over time, with handling steps removed."""
    if not points:
        return 0.0, []
    lost = 0.0
    series = [(points[0][0], 0.0)]
    for (_t0, g0), (t1, g1) in zip(points, points[1:], strict=False):
        delta = g0 - g1
        if abs(delta) > STEP_G:
            delta = 0.0  # sample pulled, topped up or moved: re-base here
        lost += delta
        series.append((t1, lost))
    return lost, series


def _smooth(series: list[tuple[datetime, float]], k: int = 3) -> list[tuple[datetime, float]]:
    out = []
    for i, (t, _v) in enumerate(series):
        window = [v for _t, v in series[max(0, i - k + 1) : i + 1]]
        out.append((t, statistics.median(window)))
    return out


def _rate_per_day(series: list[tuple[datetime, float]], end: datetime, span_s: float) -> float | None:
    start = [p for p in series if (end - p[0]).total_seconds() >= span_s]
    if not start:
        return None
    t0, v0 = start[-1]
    t1, v1 = series[-1]
    seconds = (t1 - t0).total_seconds()
    if seconds <= 0:
        return None
    return (v1 - v0) / seconds * 86400


def _rolling_rates(series: list[tuple[datetime, float]], span_s: float) -> list[float]:
    """Loss rate (g/day) over a trailing window, at every sample. One pass."""
    rates: list[float] = []
    j = 0
    for i, (t, v) in enumerate(series):
        while j + 1 < i and (t - series[j + 1][0]).total_seconds() >= span_s:
            j += 1
        seconds = (t - series[j][0]).total_seconds()
        if seconds >= span_s:
            rates.append((v - series[j][1]) / seconds * 86400)
    return rates


def weight_summary(conn: sqlite3.Connection, batch_id: int) -> dict | None:
    batch = conn.execute("SELECT * FROM BATCH WHERE id = ?", (batch_id,)).fetchone()
    if batch is None:
        return None
    rows = conn.execute(
        "SELECT ts, grams FROM WEIGHT_READING WHERE batch_id = ? AND grams IS NOT NULL ORDER BY ts", (batch_id,)
    ).fetchall()
    points = [(parse_iso(r["ts"]), float(r["grams"])) for r in rows]
    out: dict = {"points": [(r["ts"], float(r["grams"])) for r in rows], "count": len(points)}
    if len(points) < 2:
        out.update(state="waiting", text="Collecting weight readings (one every 5 minutes).")
        return out
    lost, series = fermentation_loss(points)
    series = _smooth(series)
    lost = max(0.0, series[-1][1])
    volume_l, volume_source = batch_volume_l(conn, batch)
    abv = lost / volume_l / ABV_FACTOR
    out.update(
        current_g=points[-1][1],
        start_g=points[0][1],
        lost_g=lost,
        co2_g=lost,
        volume_l=volume_l,
        volume_source=volume_source,
        abv=abv,
        sg_drop=abv / 131.25,
        est_sg=(float(batch["og"]) - abv / 131.25) if batch["og"] else None,
    )
    end = series[-1][0]
    rate = _rate_per_day(series, end, 24 * 3600) or _rate_per_day(series, end, 6 * 3600)
    rates = _rolling_rates(series, 12 * 3600)
    peak = max(rates) if rates else None
    out.update(rate_g_day=rate, peak_g_day=peak)
    window = [v for t, v in series if (end - t).total_seconds() <= STABLE_WINDOW_S]
    spans_window = (end - series[0][0]).total_seconds() >= STABLE_WINDOW_S
    stable = spans_window and window and (max(window) - min(window)) <= STABLE_BAND_G
    if lost < MIN_ACTIVITY_G and not spans_window:
        out.update(state="waiting", text="No weight loss yet. Fermentation usually shows within 12-48 hours.")
    elif stable and lost >= MIN_ACTIVITY_G:
        out.update(
            state="stable",
            text=f"Weight stable for 48 hours (within {STABLE_BAND_G:.0f} g) after losing {lost:.0f} g: "
            "fermentation has likely finished. Confirm with the hydrometer (same reading 3 days running) "
            "before bottling.",
        )
    elif stable:
        out.update(
            state="idle", text="No weight change in 48 hours and almost no loss. Check the yeast and temperature."
        )
    elif peak and rate is not None and rate < peak * SLOWING_FRACTION:
        out.update(state="slowing", text=f"Slowing down: {rate:.1f} g/day now, down from a peak of {peak:.0f} g/day.")
    else:
        out.update(state="active", text="Fermenting." if rate is None else f"Fermenting: losing {rate:.1f} g/day.")
    return out
