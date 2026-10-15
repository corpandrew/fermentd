"""A tiny, safe markdown subset for recipe guides. All input is HTML-escaped first."""

from __future__ import annotations

import html
import re
from pathlib import Path

from fermentd.profiles.recipe import categories, parse_recipe

_ROOTS = (Path(__file__).resolve().parents[3], Path.cwd())
_INLINE = (
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
    (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<![\w*])\*([^*\n]+)\*(?!\w)"), r"<em>\1</em>"),
)


def _inline(text: str) -> str:
    out = html.escape(text, quote=False)
    for pattern, repl in _INLINE:
        out = pattern.sub(repl, out)
    return out


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def render(text: str, *, checkable: bool = False, prefix: str = "") -> str:
    """Render headings, paragraphs, lists, bold, italics, and code. Ordered list items can be checkboxes."""
    parts: list[str] = []
    para: list[str] = []
    list_kind: str | None = None
    section = ""
    counter = 0

    def flush_para() -> None:
        if para:
            parts.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            parts.append(f"</{list_kind}>")
            list_kind = None

    for raw in text.splitlines():
        line = raw.rstrip()
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        ordered = re.match(r"^\d+\.\s+(.*)$", line)
        bullet = re.match(r"^[-*]\s+(.*)$", line)
        if heading:
            flush_para()
            close_list()
            level = min(len(heading.group(1)) + 1, 5)
            section = _slug(heading.group(2))
            counter = 0
            parts.append(f'<h{level} id="{prefix}{section}">{_inline(heading.group(2))}</h{level}>')
        elif ordered or bullet:
            flush_para()
            kind = "ol" if ordered else "ul"
            if list_kind != kind:
                close_list()
                css = ' class="steps"' if kind == "ol" and checkable else ""
                parts.append(f"<{kind}{css}>")
                list_kind = kind
            body = _inline((ordered or bullet).group(1))
            if kind == "ol" and checkable:
                counter += 1
                key = f"{prefix}{section}-{counter}"
                parts.append(f'<li><label><input type="checkbox" data-step="{key}"> <span>{body}</span></label></li>')
            else:
                parts.append(f"<li>{body}</li>")
        elif not line.strip():
            flush_para()
            close_list()
        else:
            close_list()
            para.append(line.strip())
    flush_para()
    close_list()
    return "\n".join(parts)


def find_recipe(relative: str | None) -> Path | None:
    if not relative:
        return None
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    for root in _ROOTS:
        candidate = root / rel
        if candidate.is_file():
            return candidate
    return None


SIZES = ("1", "0.5")
_SIZED = re.compile(r"\[\[([^|\]]*)\|([^\]]*)\]\]")


def apply_size(text: str, half: bool) -> str:
    """Pick the 1-gallon or half-gallon side of every [[full|half]] token."""
    return _SIZED.sub(lambda m: m.group(2) if half else m.group(1), text)


def load_guide(relative: str | None, *, prefix: str = "", size: str | None = "1") -> dict | None:
    path = find_recipe(relative)
    if path is None:
        return None
    recipe = parse_recipe(path.read_text())
    half_meta = recipe.pop("half", None)
    half = size == "0.5" and isinstance(half_meta, dict)
    body = apply_size(recipe.pop("body"), half)
    if half:
        recipe = {**recipe, **half_meta}
        recipe["ingredients"] = [
            {**item, "amount": item.get("amount_half", item.get("amount"))} for item in recipe.get("ingredients", [])
        ]
    headings = [m.group(1) for m in re.finditer(r"^##\s+(.*)$", body, flags=re.M)]
    layout = categories()[recipe["category"]]
    return {
        "category": recipe["category"],
        "category_label": layout["label"],
        "tiles": summary_tiles(layout["tiles"], recipe),
        "hops": hop_schedule(recipe) if layout.get("hop_table") or recipe.get("hop_table") else [],
        "name": recipe.get("name"),
        "meta": recipe,
        "html": render(body, checkable=True, prefix=prefix),
        "toc": [{"title": h, "id": f"{prefix}{_slug(h)}"} for h in headings],
        "size": "0.5" if half else "1",
        "sizes": list(SIZES) if isinstance(half_meta, dict) else ["1"],
    }


def _range(values, fmt="{:g}") -> str:
    if isinstance(values, (list, tuple)) and len(values) == 2:
        low, high = (fmt.format(v) for v in values)
        return low if low == high else f"{low}–{high}"
    return fmt.format(values)


def _hours_or_days(window) -> str:
    low, high = window
    if low >= 72:
        return f"{round(low / 24)}–{round(high / 24)} days"
    return f"{low}–{high} h"


def summary_tiles(ids: list[str], meta: dict) -> list[dict]:
    """Only the metrics that mean something for this kind of drink; a tile without data is dropped."""
    tiles: list[dict] = []
    y = meta.get("yield", {})

    def add(key: str, value) -> None:
        if value:
            tiles.append({"k": key, "v": value})

    for tile in ids:
        if tile == "makes" and y.get("volume_gal"):
            add("Makes", f"{y['volume_gal']:g} gal")
        elif tile == "bottles" and y.get("bottle_count"):
            count = str(y["bottle_count"])
            add("Bottles", count if "mL" in count else f"{count} × {y.get('bottle_fl_oz', 12):g} oz")
        elif tile == "carbonate" and meta.get("carbonation_window_h"):
            temp = meta.get("condition_f") or meta.get("target_f")
            add("Carbonate", f"{_hours_or_days(meta['carbonation_window_h'])} at {temp}°F")
        elif tile == "condition" and meta.get("carbonation_window_h"):
            temp = meta.get("condition_f") or meta.get("target_f")
            add("Condition", f"{_hours_or_days(meta['carbonation_window_h'])} at {temp}°F")
        elif tile == "og_abv" and meta.get("og_target"):
            og = _range(meta["og_target"], "{:.3f}")
            abv = f" · {_range(meta['abv_expected'])}%" if meta.get("abv_expected") else ""
            add("OG / ABV", og + abv)
        elif tile == "ibu" and meta.get("ibu"):
            add("Bitterness", f"~{meta['ibu']} IBU")
        elif tile == "ferment" and meta.get("target_f"):
            add("Ferment", f"{meta['target_f']}°F")
        elif tile == "pitch_below" and meta.get("pitch_below_f"):
            add("Pitch below", f"{meta['pitch_below_f']}°F")
        elif tile == "alcohol":
            add("Alcohol", "under ~1%")
        elif tile == "ph" and meta.get("ph_start_max"):
            add("Starting pH", f"≤ {meta['ph_start_max']}")
        elif tile == "f1":
            if meta.get("f1_days"):
                add("First ferment", f"{_range(meta['f1_days'])} days at {meta.get('target_f')}°F")
            elif meta.get("f1_hours"):
                add("First ferment", f"{_range(meta['f1_hours'])} h at {meta.get('target_f')}°F")
        elif tile == "aging" and meta.get("aging_months"):
            add("Age", f"{_range(meta['aging_months'])} months")
        elif tile == "bottle_at" and meta.get("bottle_gravity"):
            add("Bottle at", f"SG {_range(meta['bottle_gravity'], '{:.3f}')}")
        elif tile == "tirage" and meta.get("tirage_sugar_g_l"):
            add("Tirage", f"{meta['tirage_sugar_g_l']} g/L sugar · ~{meta.get('pressure_atm', 6)} atm")
        elif tile == "en_tirage" and meta.get("en_tirage_months"):
            add("En tirage", f"{_range(meta['en_tirage_months'])} months")
        elif tile == "dosage" and meta.get("dosage_g_l"):
            add("Dosage", f"{_range(meta['dosage_g_l'])} g/L (brut)")
        elif tile == "still":
            add("Finish", "still (no bubbles)")
    return tiles


_WHEN = re.compile(r"(\d+\s*minutes|flameout|dry hop|last \d+-\d+ days)", re.I)


def hop_schedule(meta: dict) -> list[dict]:
    """Hop additions in boil order, from the ingredient list (already scaled to the batch size)."""
    rows = []
    for item in meta.get("ingredients", []):
        name = item.get("item", "")
        if "hops" not in name.lower():
            continue
        text = f"{name}, {item.get('note', '')}"
        when_match = _WHEN.search(text)
        when = when_match.group(1) if when_match else "boil"
        hop = name.split(" hops")[0]
        minutes = re.match(r"(\d+)", when)
        order = -int(minutes.group(1)) if minutes else (0 if "flameout" in when.lower() else 1)
        rows.append({"hop": hop, "amount": item.get("amount"), "when": when.replace("minutes", "min"), "order": order})
    rows.sort(key=lambda row: row["order"])
    return rows
