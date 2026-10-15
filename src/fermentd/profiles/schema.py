"""Beverage profile models. A profile may only tighten the global safety limits."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fermentd.config import (
    HARD_CUTOFF_F,
    HARD_HYSTERESIS_MAX_F,
    HARD_HYSTERESIS_MIN_F,
    HARD_MAX_ON_MINUTES,
    HARD_TARGET_MAX_F,
    HARD_TARGET_MIN_F,
)

_DURATION = re.compile(r"^(\d+)(m|h|d)$")
_ANCHOR = re.compile(r"^(?:start|packaged|stage:[a-z0-9_]+)\+(\d+(?:m|h|d))$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TemperatureSpec(_Strict):
    default_target_f: float
    recommended_f: tuple[float, float]
    allowed_target_f: tuple[float, float]
    default_hysteresis_f: float


class RampSpec(_Strict):
    after: str
    target_f: float


class StageSpec(_Strict):
    id: str
    core: Literal["prep", "primary", "secondary", "packaging", "conditioning", "done"]
    optional: bool = False
    tracking: Literal["weight", "timer"] | None = None
    target_f: float | None = None  # set automatically when the batch enters this stage
    ramp: RampSpec | None = None  # then step to ramp.target_f once ramp.after has passed in the stage


class DoneRule(_Strict):
    type: Literal["absolute_and_plateau", "plateau", "timer"] = "timer"


class ReminderSpec(_Strict):
    id: str
    at: str
    text: str
    repeat: str | None = None


class Guidance(_Strict):
    headspace: str = ""
    blowoff: str = ""
    sampling: str = ""
    safety_glass: str = ""
    safety_pitch: str = ""
    note: str = ""


class AlertsSpec(_Strict):
    pressure_risk_margin_f: float = 3.0
    warm_action_f: float = 72.0
    over_target_margin_f: float = 2.0


class SafetyTighten(_Strict):
    cutoff_f: float | None = None
    max_on_minutes: int | None = None


class CarbonationSpec(_Strict):
    default: Literal["still", "sparkling"] = "sparkling"
    target_vol: float = 0.0
    max_vol: float = 3.0
    method: str = "in_bottle"


class Profile(_Strict):
    id: str
    name: str
    extends: str | None = None
    status: Literal["supported", "experimental", "unsupported_v1"]
    requires_capability: list[Literal["heat", "cool"]] = Field(min_length=1)
    tracking_mode: Literal["weight", "timer"]
    category: str | None = None
    vessel_types: list[str] = Field(default_factory=list)
    recipe: str | None = None
    default_stage: str | None = None
    temperature: TemperatureSpec
    done_rule: DoneRule = DoneRule()
    stages: list[StageSpec] = Field(min_length=1)
    reminders: list[ReminderSpec] = Field(default_factory=list)
    guidance: Guidance = Guidance()
    alerts: AlertsSpec = AlertsSpec()
    safety: SafetyTighten = SafetyTighten()
    carbonation: CarbonationSpec = CarbonationSpec()

    @model_validator(mode="after")
    def stage_rules(self) -> Profile:
        ids = [stage.id for stage in self.stages]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{self.id}: stage ids must be unique")
        if self.stages[-1].core != "done":
            raise ValueError(f"{self.id}: the last stage must map to core stage done")
        if self.default_stage is not None and self.default_stage not in ids:
            raise ValueError(f"{self.id}: default_stage {self.default_stage} is not a stage")
        reminder_ids = [item.id for item in self.reminders]
        if len(reminder_ids) != len(set(reminder_ids)):
            raise ValueError(f"{self.id}: reminder ids must be unique")
        for reminder in self.reminders:
            if _ANCHOR.match(reminder.at) is None:
                raise ValueError(f"{self.id}: bad reminder anchor {reminder.at}")
            if reminder.repeat is not None and _DURATION.match(reminder.repeat) is None:
                raise ValueError(f"{self.id}: bad reminder repeat {reminder.repeat}")
            if reminder.at.startswith("stage:"):
                stage_id = reminder.at.split("+", 1)[0].removeprefix("stage:")
                if stage_id not in ids:
                    raise ValueError(f"{self.id}: reminder {reminder.id} references unknown stage {stage_id}")
        low, high = self.temperature.allowed_target_f
        for stage in self.stages:
            for value in (stage.target_f, stage.ramp.target_f if stage.ramp else None):
                if value is not None and not (low <= value <= high):
                    raise ValueError(f"{self.id}: stage {stage.id} target {value} F is outside the allowed range")
            if stage.ramp is not None and _DURATION.match(stage.ramp.after) is None:
                raise ValueError(f"{self.id}: bad ramp duration {stage.ramp.after}")
        if low > high:
            raise ValueError(f"{self.id}: allowed target range is reversed")
        if not (low <= self.temperature.default_target_f <= high):
            raise ValueError(f"{self.id}: default target is outside the allowed range")
        return self


def duration_seconds(text: str) -> int:
    match = _DURATION.match(text)
    if match is None:
        raise ValueError(f"bad duration {text}")
    count = int(match.group(1))
    unit = match.group(2)
    scale = {"m": 60, "h": 3600, "d": 86400}[unit]
    return count * scale


def anchor_offset_seconds(anchor: str) -> int:
    if _ANCHOR.match(anchor) is None:
        raise ValueError(f"bad anchor {anchor}")
    return duration_seconds(anchor.split("+", 1)[1])


def check_against_globals(
    profile: Profile,
    *,
    target_min_f: float = HARD_TARGET_MIN_F,
    target_max_f: float = HARD_TARGET_MAX_F,
    hysteresis_min_f: float = HARD_HYSTERESIS_MIN_F,
    hysteresis_max_f: float = HARD_HYSTERESIS_MAX_F,
    cutoff_f: float = HARD_CUTOFF_F,
    max_on_minutes: int = HARD_MAX_ON_MINUTES,
    carbonation_max_vol: float = 3.0,
) -> None:
    low, high = profile.temperature.allowed_target_f
    if low < target_min_f or high > target_max_f:
        raise ValueError(
            f"{profile.id}: allowed target {low}-{high} F is outside the global {target_min_f}-{target_max_f} F"
        )
    hysteresis = profile.temperature.default_hysteresis_f
    if not (hysteresis_min_f <= hysteresis <= hysteresis_max_f):
        raise ValueError(f"{profile.id}: hysteresis {hysteresis} F is outside the global bounds")
    if profile.safety.cutoff_f is not None and profile.safety.cutoff_f > cutoff_f:
        raise ValueError(f"{profile.id}: cutoff_f {profile.safety.cutoff_f} loosens the global {cutoff_f} F cutoff")
    if profile.safety.max_on_minutes is not None and profile.safety.max_on_minutes > max_on_minutes:
        raise ValueError(f"{profile.id}: max_on_minutes loosens the global {max_on_minutes} minute cap")
    if profile.carbonation.max_vol > carbonation_max_vol:
        raise ValueError(f"{profile.id}: max_vol {profile.carbonation.max_vol} exceeds {carbonation_max_vol}")
