"""Console and log notifier. Enough until a real delivery backend exists."""

from __future__ import annotations

import logging

LOG = logging.getLogger("fermentd")


class LogNotifier:
    def notify(self, kind: str, severity: str, title: str, body: str) -> None:
        if kind == "digest" or severity in {"action", "critical"}:
            LOG.warning("%s %s: %s — %s", severity, kind, title, body)
