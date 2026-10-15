"""Load built-in profiles and optional user overrides."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from fermentd.profiles.schema import Profile, check_against_globals
from fermentd.control.prep import with_prep

BUILTIN = Path(__file__).parent / "builtin"


def load_profiles(user_dir: Path | None = None) -> dict[str, Profile]:
    raw = _read_dir(BUILTIN)
    if user_dir is not None and user_dir.exists():
        for profile_id, document in _read_dir(user_dir).items():
            if profile_id in raw:
                raw[profile_id] = _merge(raw[profile_id], document)
            else:
                raw[profile_id] = document
    resolved: dict[str, Any] = {}
    for profile_id in raw:
        resolved[profile_id] = _resolve(profile_id, raw, [])
    profiles: dict[str, Profile] = {}
    for profile_id, document in resolved.items():
        profile = with_prep(Profile.model_validate(document))
        check_against_globals(profile)
        profiles[profile_id] = profile
    return profiles


def persist_profiles(conn: Any, profiles: dict[str, Profile], loaded_at: str) -> None:
    for profile in profiles.values():
        digest = content_hash(profile)
        row = conn.execute(
            """
            SELECT version, content_hash FROM BEVERAGE_PROFILE
            WHERE id = ? ORDER BY version DESC LIMIT 1
            """,
            (profile.id,),
        ).fetchone()
        if row is not None and row["content_hash"] == digest:
            continue
        version = 1 if row is None else int(row["version"]) + 1
        conn.execute(
            """
            INSERT INTO BEVERAGE_PROFILE (
                id, version, name, extends, source, status, definition_json, content_hash, loaded_at
            ) VALUES (?, ?, ?, ?, 'builtin', ?, ?, ?, ?)
            """,
            (
                profile.id,
                version,
                profile.name,
                profile.extends,
                profile.status,
                json.dumps(profile.model_dump(mode="json")),
                digest,
                loaded_at,
            ),
        )


def content_hash(profile: Profile) -> str:
    payload = profile.model_dump(mode="json")
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _read_dir(directory: Path) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.yaml")):
        document = yaml.safe_load(path.read_text())
        if not isinstance(document, dict) or "id" not in document:
            raise ValueError(f"{path} must be a profile mapping with an id")
        found[str(document["id"])] = document
    return found


def _resolve(profile_id: str, raw: dict[str, dict[str, Any]], stack: list[str]) -> dict[str, Any]:
    if profile_id in stack:
        raise ValueError(f"profile extends cycle: {' -> '.join([*stack, profile_id])}")
    document = raw[profile_id]
    parent = document.get("extends")
    if not parent:
        return document
    if parent not in raw:
        raise ValueError(f"{profile_id} extends unknown profile {parent}")
    base = _resolve(parent, raw, [*stack, profile_id])
    return _merge(base, document)


def _merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            if key in merged:
                merged[key] = _merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    if isinstance(base, list) and isinstance(override, list) and _list_has_ids(base):
        by_id = {item["id"]: dict(item) for item in base}
        order = [item["id"] for item in base]
        for item in override:
            item_id = item.get("id") if isinstance(item, dict) else None
            if item_id in by_id:
                by_id[item_id] = _merge(by_id[item_id], item)
            else:
                key = item_id or f"extra-{len(order)}"
                by_id[key] = item
                order.append(key)
        return [by_id[key] for key in order]
    return override


def _list_has_ids(items: list[Any]) -> bool:
    return bool(items) and all(isinstance(item, dict) and "id" in item for item in items)


def profile_safety_errors(profile: Profile, config: Any = None) -> str | None:
    """Return why a profile breaks the safety limits, or None."""
    kwargs: dict[str, Any] = {}
    if config is not None:
        kwargs = {
            "target_min_f": config.control.target_min_f,
            "target_max_f": config.control.target_max_f,
            "hysteresis_min_f": config.control.hysteresis_min_f,
            "hysteresis_max_f": config.control.hysteresis_max_f,
            "cutoff_f": min(config.safety.cutoff_f, 80.0),
            "max_on_minutes": config.safety.max_on_minutes,
            "carbonation_max_vol": config.profiles.carbonation_max_vol,
        }
    try:
        check_against_globals(profile, **kwargs)
    except ValueError as exc:
        return str(exc)
    if profile.safety.cutoff_f is not None:
        if profile.safety.cutoff_f > 80.0:
            return f"{profile.id}: cutoff_f may not be above 80 F"
        if profile.safety.cutoff_f <= profile.temperature.allowed_target_f[1]:
            return f"{profile.id}: cutoff_f must be above the highest allowed target"
    return None


def load_user_profiles(conn: Any, config: Any = None) -> dict[str, Profile]:
    """Latest version of each profile saved from the dashboard. Invalid rows are skipped."""
    rows = conn.execute(
        """
        SELECT p.* FROM BEVERAGE_PROFILE p
        WHERE p.source = 'user' AND p.version = (
            SELECT MAX(version) FROM BEVERAGE_PROFILE q WHERE q.id = p.id
        )
        """
    ).fetchall()
    found: dict[str, Profile] = {}
    for row in rows:
        try:
            profile = with_prep(Profile.model_validate(json.loads(row["definition_json"])))
        except ValueError:
            continue
        if profile_safety_errors(profile, config) is None:
            found[profile.id] = profile
    return found


def save_user_profile(conn: Any, profile: Profile, saved_at: str) -> int:
    row = conn.execute(
        "SELECT version, source FROM BEVERAGE_PROFILE WHERE id = ? ORDER BY version DESC LIMIT 1",
        (profile.id,),
    ).fetchone()
    if row is not None and row["source"] != "user":
        raise ValueError(f"{profile.id} is a built-in profile and is read-only")
    version = 1 if row is None else int(row["version"]) + 1
    conn.execute(
        """
        INSERT INTO BEVERAGE_PROFILE (
            id, version, name, extends, source, status, definition_json, content_hash, loaded_at
        ) VALUES (?, ?, ?, ?, 'user', ?, ?, ?, ?)
        """,
        (
            profile.id,
            version,
            profile.name,
            profile.extends,
            profile.status,
            json.dumps(profile.model_dump(mode="json")),
            content_hash(profile),
            saved_at,
        ),
    )
    return version
