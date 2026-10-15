"""UTC timestamps stored as ISO-8601 strings that sort in time order."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

SITE_ZONE = ZoneInfo("America/New_York")


def isoformat(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def format_local(text: str) -> str:
    moment = parse_iso(text).astimezone(SITE_ZONE)
    hour = moment.strftime("%I").lstrip("0")
    return f"{moment.strftime('%b')} {moment.day}, {hour}:{moment.strftime('%M %p')}"


def describe_due(text: str, now: str) -> str:
    when = format_local(text)
    seconds = (parse_iso(text) - parse_iso(now)).total_seconds()
    if seconds > 90:
        return f"Due {when}"
    if seconds >= -90:
        return f"Due now, {when}"
    return f"Overdue since {when}"
