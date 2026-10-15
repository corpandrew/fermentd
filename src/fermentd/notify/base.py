"""Pluggable notifications. Action-needed alerts and the weekly digest both go through this."""

from __future__ import annotations

from typing import Protocol


class Notifier(Protocol):
    def notify(self, kind: str, severity: str, title: str, body: str) -> None: ...
