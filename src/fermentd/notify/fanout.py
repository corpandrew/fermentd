"""Deliver one notification through every configured backend."""

from __future__ import annotations

import logging
from pathlib import Path

from fermentd.clock import Clock
from fermentd.config import Secrets
from fermentd.notify.base import Notifier
from fermentd.notify.log import LogNotifier
from fermentd.notify.ntfy import NtfyNotifier
from fermentd.notify.outbox import OutboxNotifier

LOG = logging.getLogger("fermentd")


class Fanout:
    def __init__(self, notifiers: list[Notifier]) -> None:
        self._notifiers = notifiers

    def notify(self, kind: str, severity: str, title: str, body: str) -> None:
        for notifier in self._notifiers:
            try:
                notifier.notify(kind, severity, title, body)
            except Exception:
                LOG.warning("notifier %s failed", type(notifier).__name__, exc_info=True)


def build_notifier(
    secrets: Secrets,
    *,
    database: Path | None = None,
    clock: Clock | None = None,
    click: str | None = None,
) -> Fanout:
    notifiers: list[Notifier] = [LogNotifier()]
    if secrets.ntfy is not None:
        inner = NtfyNotifier(
            secrets.ntfy.topic,
            secrets.ntfy.server,
            secrets.ntfy.token,
            click=click,
        )
        if database is not None and clock is not None:
            notifiers.append(OutboxNotifier(database, clock, inner))
        else:
            notifiers.append(inner)
    return Fanout(notifiers)


def start_delivery(notifier: Fanout) -> None:
    for item in notifier._notifiers:
        start = getattr(item, "start", None)
        if callable(start):
            start()


def finish_delivery(notifier: Fanout) -> None:
    for item in notifier._notifiers:
        finish = getattr(item, "finish", None)
        if callable(finish):
            finish()
