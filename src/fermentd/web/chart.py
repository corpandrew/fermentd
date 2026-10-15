"""Temperature chart as inline SVG. One drawing path for the page and the poll."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from fermentd.timefmt import SITE_ZONE, format_local, parse_iso
from fermentd.web.status import format_temp

_WIDTH = 720
_HEIGHT = 250
_LEFT = 52
_RIGHT = 16
_TOP = 16
_PLOT_H = 190


def render_temperature_chart(
    points: list[dict],
    *,
    target_f: float | None,
    hysteresis_f: float | None,
) -> str:
    usable = [point for point in points if point["vessel_temp_f"] is not None or point["ambient_temp_f"] is not None]
    if not usable:
        return _empty()
    values = [point["vessel_temp_f"] for point in usable if point["vessel_temp_f"] is not None]
    values += [point["ambient_temp_f"] for point in usable if point["ambient_temp_f"] is not None]
    if target_f is not None:
        values.append(target_f)
        if hysteresis_f:
            values.append(target_f - hysteresis_f)
    low = min(values) - 1.5
    high = max(values) + 1.5
    if high - low < 8:
        middle = (high + low) / 2
        low, high = middle - 4, middle + 4
    step = _nice_step(high - low)
    low = math.floor(low / step) * step
    high = math.ceil(high / step) * step
    plot_w = _WIDTH - _LEFT - _RIGHT
    plot_bottom = _TOP + _PLOT_H

    def y_of(temp: float) -> float:
        return _TOP + (high - temp) / (high - low) * _PLOT_H

    t0 = parse_iso(usable[0]["ts"]).timestamp()
    t1 = parse_iso(usable[-1]["ts"]).timestamp()
    span = max(t1 - t0, 1.0)

    def x_at(epoch: float) -> float:
        return _LEFT + (epoch - t0) / span * plot_w

    def x_of(ts: str) -> float:
        return x_at(parse_iso(ts).timestamp())

    parts = [
        f'<svg class="tchart" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_WIDTH} {_HEIGHT}" '
        'role="img" aria-label="Bottle and room temperature over the last day">',
    ]
    parts.extend(_heater(usable, x_of, plot_w))
    value = low
    while value <= high + 1e-9:
        y = y_of(value)
        parts.append(f'<line class="grid" x1="{_LEFT}" y1="{y:.1f}" x2="{_LEFT + plot_w}" y2="{y:.1f}"/>')
        parts.append(_label(_LEFT - 8, y + 4, f"{value:g}°", anchor="end"))
        value += step
    for epoch in _time_ticks(t0, t1):
        x = x_at(epoch)
        parts.append(f'<line class="grid v" x1="{x:.1f}" y1="{_TOP}" x2="{x:.1f}" y2="{plot_bottom}"/>')
        parts.append(_label(x, plot_bottom + 18, _hour(epoch, span), anchor="middle"))
    if target_f is not None and hysteresis_f:
        band_top = y_of(target_f)
        band_height = y_of(target_f - hysteresis_f) - band_top
        parts.append(
            f'<rect class="band" x="{_LEFT}" y="{band_top:.1f}" width="{plot_w}" height="{band_height:.1f}"/>'
        )
    if target_f is not None:
        y = y_of(target_f)
        parts.append(f'<line class="target" x1="{_LEFT}" y1="{y:.1f}" x2="{_LEFT + plot_w}" y2="{y:.1f}"/>')
        parts.append(_label(_LEFT + plot_w - 6, y - 6, f"Target {format_temp(target_f)}", anchor="end", cls="tlabel"))
    parts.append(_series(usable, "ambient_temp_f", x_of, y_of, "room"))
    parts.append(_series(usable, "vessel_temp_f", x_of, y_of, "vessel"))
    parts.extend(_duty_bars(usable, t0, t1, x_at, plot_bottom))
    parts.append(f'<rect class="frame" x="{_LEFT}" y="{_TOP}" width="{plot_w}" height="{_PLOT_H}"/>')
    parts.append(_label(_LEFT, _HEIGHT - 4, format_local(usable[0]["ts"]), anchor="start", cls="dim"))
    parts.append(_label(_LEFT + plot_w, _HEIGHT - 4, format_local(usable[-1]["ts"]), anchor="end", cls="dim"))
    parts.append("</svg>")
    return "".join(parts)


def _nice_step(span: float) -> float:
    for step in (1, 2, 5, 10, 20):
        if span / step <= 6:
            return float(step)
    return 50.0


def _time_ticks(t0: float, t1: float) -> list[float]:
    span = t1 - t0
    if span <= 0:
        return []
    for hours in (0.25, 0.5, 1, 2, 3, 4, 6, 12, 24, 48, 72, 168):
        if span / (hours * 3600) <= 7:
            break
    size = hours * 3600
    first = math.ceil(t0 / size) * size
    ticks = []
    tick = first
    while tick < t1 - size * 0.15:
        if tick > t0 + size * 0.15:
            ticks.append(tick)
        tick += size
    return ticks


def _hour(epoch: float, span: float) -> str:
    moment = datetime.fromtimestamp(epoch, UTC).astimezone(SITE_ZONE)
    hour = moment.strftime("%I").lstrip("0") + moment.strftime(":%M %p").replace(":00", "")
    if span > 2 * 86400:
        return f"{moment.strftime('%b')} {moment.day}"
    return hour.lower()


def _empty() -> str:
    return (
        f'<svg class="tchart" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_WIDTH} 120" '
        'role="img" aria-label="Temperature chart waiting for readings">'
        f'<text class="empty" x="{_WIDTH / 2}" y="64" text-anchor="middle">'
        "Waiting for readings. The chart fills in as the probe reports."
        "</text></svg>"
    )


def _series(points: list[dict], key: str, x_of, y_of, cls: str) -> str:
    chunks: list[list[str]] = []
    current: list[str] = []
    for point in points:
        value = point[key]
        if value is None:
            if current:
                chunks.append(current)
                current = []
            continue
        current.append(f"{x_of(point['ts']):.1f},{y_of(value):.1f}")
    if current:
        chunks.append(current)
    parts = []
    for chunk in chunks:
        if len(chunk) == 1:
            x, y = chunk[0].split(",")
            parts.append(f'<circle class="dot {cls}" cx="{x}" cy="{y}" r="3.5"/>')
        else:
            parts.append(f'<polyline class="line {cls}" points="{" ".join(chunk)}"/>')
    return "".join(parts)


def _heater(points: list[dict], x_of, plot_w: float) -> list[str]:
    parts = []
    run_start = None
    for index, point in enumerate(points):
        if point["heater_on"] and run_start is None:
            run_start = index
        ending = run_start is not None and (not point["heater_on"] or index == len(points) - 1)
        if not ending:
            continue
        end = index if point["heater_on"] else index - 1
        x1 = x_of(points[run_start]["ts"])
        x2 = x_of(points[end]["ts"])
        if x2 <= x1:
            x2 = x1 + 2
        parts.append(f'<rect class="heat" x="{x1:.1f}" y="{_TOP}" width="{x2 - x1:.1f}" height="{_PLOT_H}"/>')
        run_start = None
    return parts


_DUTY_H = 36.0


def hourly_duty(points: list[dict]) -> list[tuple[float, float]]:
    """(hour start epoch, fraction of readings with the heater on) per clock hour."""
    buckets: dict[float, list[int]] = {}
    for point in points:
        epoch = parse_iso(point["ts"]).timestamp()
        hour = epoch - epoch % 3600
        buckets.setdefault(hour, []).append(1 if point["heater_on"] else 0)
    return [(hour, sum(v) / len(v)) for hour, v in sorted(buckets.items())]


def _duty_bars(points: list[dict], t0: float, t1: float, x_at, plot_bottom: float) -> list[str]:
    """Heat-mat percent-on per hour as small bars along the bottom of the plot."""
    parts = []
    for hour, duty in hourly_duty(points):
        x1 = x_at(max(hour, t0))
        x2 = x_at(min(hour + 3600, t1))
        if x2 - x1 < 1:
            x2 = x1 + 1
        height = duty * _DUTY_H
        title = f"{round(duty * 100)}% heat"
        parts.append(
            f'<rect class="duty" x="{x1 + 0.5:.1f}" y="{plot_bottom - height:.1f}" '
            f'width="{max(x2 - x1 - 1, 1):.1f}" height="{height:.1f}"><title>{title}</title></rect>'
        )
        if x2 - x1 >= 22 and duty > 0:
            parts.append(_label((x1 + x2) / 2, plot_bottom - height - 3, f"{round(duty * 100)}%", "middle", "duty-l"))
    return parts


def _label(x: float, y: float, text: str, anchor: str = "start", cls: str = "") -> str:
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    klass = f"lbl {cls}".strip()
    return f'<text class="{klass}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}">{safe}</text>'


def render_weight_chart(points: list[tuple[str, float]]) -> str:
    """Batch weight (g) over time. Points are (iso ts, grams); thinned to about 400 for the page."""
    if len(points) < 2:
        return _empty()
    step = max(1, len(points) // 400)
    pts = [(parse_iso(ts).timestamp(), g) for ts, g in points[::step]]
    if pts[-1][0] != parse_iso(points[-1][0]).timestamp():
        pts.append((parse_iso(points[-1][0]).timestamp(), points[-1][1]))
    t0, t1 = pts[0][0], pts[-1][0]
    lo, hi = min(g for _t, g in pts), max(g for _t, g in pts)
    pad = max(5.0, (hi - lo) * 0.1)
    lo, hi = lo - pad, hi + pad
    plot_w = _WIDTH - _LEFT - _RIGHT

    def x_of(t: float) -> float:
        return _LEFT + (t - t0) / max(1.0, t1 - t0) * plot_w

    def y_of(g: float) -> float:
        return _TOP + (hi - g) / (hi - lo) * _PLOT_H

    parts = [f'<svg class="tchart wchart" viewBox="0 0 {_WIDTH} {_HEIGHT}" role="img" aria-label="Weight over time">']
    gstep = next((v for v in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000) if (hi - lo) / v <= 6), 5000)
    g = math.ceil(lo / gstep) * gstep
    while g <= hi:
        y = y_of(g)
        parts.append(f'<line class="grid" x1="{_LEFT}" x2="{_WIDTH - _RIGHT}" y1="{y:.1f}" y2="{y:.1f}"/>')
        parts.append(_label(_LEFT - 6, y + 4, f"{g:,.0f} g", "end", "lbl"))
        g += gstep
    for t in _time_ticks(t0, t1):
        parts.append(_label(x_of(t), _TOP + _PLOT_H + 18, _hour(t, t1 - t0), "middle", "lbl"))
    path = " ".join(f"{'M' if i == 0 else 'L'}{x_of(t):.1f},{y_of(gv):.1f}" for i, (t, gv) in enumerate(pts))
    parts.append(f'<path class="line vessel" d="{path}" fill="none"/>')
    parts.append("</svg>")
    return "".join(parts)
