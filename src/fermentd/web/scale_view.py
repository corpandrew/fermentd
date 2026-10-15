"""Dashboard view of a vessel's scale: status, calibration state, and the weight summary."""

from __future__ import annotations

import sqlite3

from fermentd.control.weight import ABV_FACTOR, STABLE_BAND_G, weight_summary
from fermentd.timefmt import format_local
from fermentd.web.chart import render_weight_chart

_STATUS = {
    "ok": "Scale connected",
    "not_connected": "Scale not connected",
    "needs_tare": "Scale needs tare (empty platform)",
    "needs_calibration": "Scale needs calibration with a known weight",
    "unknown": "Waiting for the first scale reading",
}


def scale_panel(conn: sqlite3.Connection, vessel_id: str, batch_id: int | None) -> dict | None:
    row = conn.execute("SELECT * FROM SCALE WHERE vessel_id = ?", (vessel_id,)).fetchone()
    if row is None:
        return None
    panel: dict = {
        "status": row["status"],
        "status_label": _STATUS.get(row["status"], row["status"]),
        "detail": row["status_detail"],
        "checked": format_local(row["status_at"]) if row["status_at"] else None,
        "driver": row["driver"],
        "tared": format_local(row["tared_at"]) if row["tared_at"] else None,
        "calibrated": format_local(row["calibrated_at"]) if row["calibrated_at"] else None,
        "cal_weight": f"{row['cal_weight_g']:.0f} g" if row["cal_weight_g"] else None,
        "summary": None,
        "chart": None,
        "assumptions": (
            f"Assumes all weight lost is CO2 leaving through the airlock. ABV ≈ CO2 g ÷ litres ÷ {ABV_FACTOR}; "
            "gravity drop ≈ ABV ÷ 131.25. Sudden drops over 30 g (hydrometer samples, moving the jug) are ignored. "
            f"'Stable' means within {STABLE_BAND_G:.0f} g for 48 hours. A hydrometer is still the final word."
        ),
    }
    if batch_id is None:
        return panel
    summary = weight_summary(conn, batch_id)
    if summary:
        panel["summary"] = summary
        panel["chart"] = render_weight_chart(summary["points"]) if summary["count"] >= 2 else None
        if "lost_g" in summary:
            tiles = [
                ("Now", f"{summary['current_g']:,.0f} g"),
                ("Lost since start", f"{summary['lost_g']:,.0f} g"),
                ("CO2 released (est.)", f"{summary['co2_g']:,.0f} g"),
                ("ABV (est.)", f"{summary['abv']:.1f}%"),
            ]
            if summary.get("est_sg") is not None:
                tiles.append(("Gravity (est.)", f"{summary['est_sg']:.3f}"))
            else:
                tiles.append(("Gravity drop (est.)", f"{summary['sg_drop'] * 1000:.0f} points"))
            if summary.get("rate_g_day") is not None:
                tiles.append(("Activity", f"{summary['rate_g_day']:.1f} g/day"))
            panel["tiles"] = tiles
            panel["volume_note"] = f"Volume {summary['volume_l']:.2f} L ({summary['volume_source']})."
    return panel
