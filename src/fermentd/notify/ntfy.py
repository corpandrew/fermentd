"""Send action, critical, and digest notifications to a phone through ntfy."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

LOG = logging.getLogger("fermentd")
# Informational kinds that are still worth a phone push.
PUSH_INFO_KINDS = {"digest", "target_reached", "probe_recovered", "fermentation_slowing"}


def _request(url: str, body: str, headers: dict[str, str], method: str = "POST") -> bytes:
    data = None if method == "DELETE" else body.encode()
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read()


def _message_id(raw: bytes | str | None) -> str | None:
    if not raw:
        return None
    text = raw.decode() if isinstance(raw, bytes) else raw
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    message_id = payload.get("id")
    if isinstance(message_id, str) and message_id:
        return message_id
    return None


class NtfyNotifier:
    def __init__(
        self,
        topic: str,
        server: str = "https://ntfy.sh",
        token: str | None = None,
        post=None,
        click: str | None = None,
    ) -> None:
        self.topic = topic
        self.server = server.rstrip("/")
        self.token = token or None
        self.click = click or None
        self._post = post or _request

    def notify(self, kind: str, severity: str, title: str, body: str) -> None:
        self.deliver(kind, severity, title, body)

    def deliver(self, kind: str, severity: str, title: str, body: str) -> bool:
        if kind not in PUSH_INFO_KINDS and severity not in {"action", "critical"}:
            return True
        try:
            self._post(f"{self.server}/{self.topic}", body, self._headers(title, severity))
            return True
        except (OSError, urllib.error.URLError):
            LOG.warning("ntfy delivery failed for %s", kind, exc_info=True)
            return False

    def schedule(self, title: str, body: str, *, severity: str, delay: str) -> str | None:
        headers = self._headers(title, severity)
        headers["Delay"] = delay
        try:
            raw = self._post(f"{self.server}/{self.topic}", body, headers)
        except (OSError, urllib.error.URLError):
            LOG.warning("ntfy schedule failed", exc_info=True)
            return None
        return _message_id(raw)

    def cancel(self, message_id: str) -> bool:
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            self._post(f"{self.server}/{self.topic}/{message_id}", "", headers, "DELETE")
            return True
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return True
            LOG.warning("ntfy cancel failed for %s", message_id, exc_info=True)
            return False
        except (OSError, urllib.error.URLError):
            LOG.warning("ntfy cancel failed for %s", message_id, exc_info=True)
            return False

    def _headers(self, title: str, severity: str) -> dict[str, str]:
        headers = {
            "Title": title,
            "Priority": _priority(severity),
            "Content-Type": "text/plain; charset=utf-8",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.click:
            headers["Click"] = self.click
        return headers


def _priority(severity: str) -> str:
    if severity == "critical":
        return "urgent"
    if severity == "action":
        return "high"
    return "default"
