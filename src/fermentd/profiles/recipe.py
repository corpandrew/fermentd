"""Parse a fermentd.recipe/v1 markdown file. The YAML frontmatter is the source of truth."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CATEGORIES_FILE = Path(__file__).parent / "categories.yaml"
_CATEGORIES: dict[str, Any] | None = None


def categories() -> dict[str, Any]:
    """Per-category guide layout: section order, required sections and summary tiles."""
    global _CATEGORIES
    if _CATEGORIES is None:
        _CATEGORIES = yaml.safe_load(CATEGORIES_FILE.read_text())
    return _CATEGORIES


def required_sections(category: str) -> list[str]:
    return list(categories()[category]["required"])


def parse_recipe(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        raise ValueError("recipe must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("recipe frontmatter is not closed")
    data = yaml.safe_load(text[4:end])
    if not isinstance(data, dict):
        raise ValueError("recipe frontmatter must be a mapping")
    if data.get("schema") != "fermentd.recipe/v1":
        raise ValueError("recipe schema must be fermentd.recipe/v1")
    body = text[end + 5 :]
    category = data.get("category")
    if category not in categories():
        raise ValueError(f"recipe category must be one of {', '.join(categories())}")
    headings = [line[3:].strip() for line in body.splitlines() if line.startswith("## ")]
    missing = [heading for heading in required_sections(category) if heading not in headings]
    if missing:
        raise ValueError(f"recipe is missing headings: {', '.join(missing)}")
    allowed = categories()[category]["sections"]
    unknown = [heading for heading in headings if heading not in allowed]
    if unknown:
        raise ValueError(f"{category} recipe has sections not in its layout: {', '.join(unknown)}")
    order = [allowed.index(heading) for heading in headings]
    if order != sorted(order):
        raise ValueError(f"{category} recipe sections are out of process order")
    data["body"] = body
    return data


def load_recipe(path: Path) -> dict[str, Any]:
    return parse_recipe(path.read_text())
