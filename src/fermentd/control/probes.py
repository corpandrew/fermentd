"""Turn raw temperature samples into healthy or faulted probe state."""

from __future__ import annotations

from dataclasses import dataclass

from fermentd.drivers.base import TempSample
from fermentd.drivers.ds18b20 import rate_reject

HEALTHY_CLEAR_S = 300.0


@dataclass
class ProbeHealth:
    consecutive_rejects: int = 0
    faulted: bool = False
    healthy_since: float | None = None
    last_good_f: float | None = None
    last_good_mono: float | None = None
    temp_f: float | None = None
    reject_reason: str | None = None


def observe(
    state: ProbeHealth,
    sample: TempSample,
    now_mono: float,
    max_rate_f_per_min: float,
) -> ProbeHealth:
    reason = sample.reject_reason
    temp_f = sample.temp_f
    if reason is None and temp_f is not None:
        rate = rate_reject(state.last_good_f, state.last_good_mono, temp_f, now_mono, max_rate_f_per_min)
        if rate is not None:
            reason = rate
            temp_f = None
    if reason is None and temp_f is not None:
        faulted = state.faulted
        healthy_since = state.healthy_since
        if faulted:
            if healthy_since is None:
                healthy_since = now_mono
            elif now_mono - healthy_since >= HEALTHY_CLEAR_S:
                faulted = False
                healthy_since = None
        return ProbeHealth(
            consecutive_rejects=0,
            faulted=faulted,
            healthy_since=healthy_since,
            last_good_f=temp_f,
            last_good_mono=now_mono,
            temp_f=temp_f,
            reject_reason=None,
        )
    rejects = 3 if reason == "missing" else state.consecutive_rejects + 1
    return ProbeHealth(
        consecutive_rejects=rejects,
        faulted=state.faulted or reason == "missing" or rejects >= 3,
        healthy_since=None,
        last_good_f=state.last_good_f,
        last_good_mono=state.last_good_mono,
        temp_f=None,
        reject_reason=reason,
    )
