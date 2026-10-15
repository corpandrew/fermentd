"""Load and validate fermentd.yaml. Unknown keys are errors."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Absolute ceilings. A config file may tighten these and must not loosen them.
HARD_CUTOFF_F = 80.0
HARD_TARGET_MIN_F = 50.0
HARD_TARGET_MAX_F = 75.0
HARD_HYSTERESIS_MIN_F = 0.5
HARD_HYSTERESIS_MAX_F = 3.0
HARD_MAX_ON_MINUTES = 240
HARD_REST_MINUTES = 15


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SiteConfig(_Strict):
    name: str
    timezone: str


class DatabaseConfig(_Strict):
    path: str
    backup_dir: str
    raw_retention_days: int = 30


class OneWireConfig(_Strict):
    gpio: int
    sysfs_root: str = "/sys/bus/w1/devices"
    ambient_probe: str


class HeaterConfig(_Strict):
    driver: Literal["tuya", "sim", "none"]
    device_id_ref: str | None = None
    ip: str | None = None
    protocol_version: str = "3.3"
    switch_dp: int = 1
    countdown_dp: int | None = None


class ZoneConfig(_Strict):
    id: str
    name: str
    capability: Literal["heat"]
    mode: Literal["auto", "test"] = "auto"
    heater: HeaterConfig
    default_target_f: float
    default_hysteresis_f: float
    min_on_minutes: int = 5
    min_off_minutes: int = 5


class Hx711Config(_Strict):
    """Legacy key (`hx711:`). Prefer `scale:`; an hx711 block is read as a scale with driver hx711."""

    dout_gpio: int
    sck_gpio: int
    samples: int = 15


class ScaleConfig(_Strict):
    """Optional load-cell scale under a vessel. Tare and calibration done from the dashboard or
    `fermentd-ctl scale-tare/scale-calibrate` are stored in the database and win over these seeds."""

    driver: Literal["hx711", "sim", "none"] = "none"
    dout_gpio: int = 5  # physical pin 29
    sck_gpio: int = 6  # physical pin 31
    samples: int = 15
    sample_interval_s: int = Field(default=300, ge=30, le=3600)
    tare_offset: float | None = None
    counts_per_gram: float | None = None


class VesselConfig(_Strict):
    id: str
    name: str
    vessel_type: Literal["jug", "carboy", "bucket", "jar", "bottle_group"]
    capacity_l: float | None = None
    enabled: bool = True
    temp_zone: str | None
    hx711: Hx711Config | None = None
    scale: ScaleConfig | None = None
    probe_rom_id: str | None = None

    @model_validator(mode="after")
    def legacy_hx711(self) -> VesselConfig:
        if self.hx711 is not None and self.scale is None:
            self.scale = ScaleConfig(
                driver="hx711", dout_gpio=self.hx711.dout_gpio, sck_gpio=self.hx711.sck_gpio, samples=self.hx711.samples
            )
        return self

    @property
    def scale_enabled(self) -> bool:
        return self.scale is not None and self.scale.driver != "none"


class SafetyConfig(_Strict):
    cutoff_f: float = HARD_CUTOFF_F
    cutoff_clear_f: float = 78.0
    max_on_minutes: int = HARD_MAX_ON_MINUTES
    rest_minutes: int = HARD_REST_MINUTES
    probe_min_f: float = 32.0
    probe_max_f: float = 120.0
    max_rate_f_per_min: float = 5.0
    ambient_fault_disables_heat: bool = True
    plug_unreachable_alert_after_s: int = 180

    @model_validator(mode="after")
    def ceilings(self) -> SafetyConfig:
        if self.cutoff_f > HARD_CUTOFF_F:
            raise ValueError(f"cutoff_f {self.cutoff_f} loosens the hard ceiling of {HARD_CUTOFF_F} F")
        if self.cutoff_clear_f >= self.cutoff_f:
            raise ValueError("cutoff_clear_f must be below cutoff_f")
        if self.max_on_minutes > HARD_MAX_ON_MINUTES:
            raise ValueError(
                f"max_on_minutes {self.max_on_minutes} loosens the hard ceiling of {HARD_MAX_ON_MINUTES}"
            )
        if self.rest_minutes < HARD_REST_MINUTES:
            raise ValueError(f"rest_minutes {self.rest_minutes} is shorter than the hard minimum {HARD_REST_MINUTES}")
        return self


class TuningOverride(_Strict):
    """Per-vessel heat tuning override (see fermentd.control.tuning). Every field is optional."""

    mode: Literal["onoff", "proportional"] | None = None
    overshoot_f: float | None = Field(default=None, ge=0, le=2)
    on_below_f: float | None = Field(default=None, ge=0, le=3)
    min_on_min: float | None = Field(default=None, ge=1, le=60)
    min_off_min: float | None = Field(default=None, ge=1, le=60)
    smoothing: int | None = Field(default=None, ge=1, le=5)
    window_min: float | None = Field(default=None, ge=10, le=120)
    base_duty: float | None = Field(default=None, ge=0, le=1)
    gain_per_f: float | None = Field(default=None, ge=0, le=2)
    max_duty: float | None = Field(default=None, ge=0, le=1)
    hot_cut_f: float | None = Field(default=None, ge=0, le=2)


class ControlConfig(_Strict):
    target_min_f: float = HARD_TARGET_MIN_F
    target_max_f: float = HARD_TARGET_MAX_F
    hysteresis_min_f: float = HARD_HYSTERESIS_MIN_F
    hysteresis_max_f: float = HARD_HYSTERESIS_MAX_F
    over_target_margin_f: float = 2.0
    over_target_minutes: int = 120
    probe_silent_s: int = 120
    heater_stuck_minutes: int = 45
    heater_stuck_min_rise_f: float = 0.5
    heater_stuck_repeat_minutes: int = 180
    slowing_fraction: float = 0.10
    slowing_min_peak_g_day: float = 10.0
    # Keyed by vessel id or vessel type (jug, bottle_group, ...); the id wins.
    tuning: dict[str, TuningOverride] = Field(default_factory=dict)
    # Quiet period for warnings after a stage change, and for a probe that was just moved.
    stage_change_grace_minutes: int = 120
    probe_settle_minutes: int = 10

    @model_validator(mode="after")
    def ceilings(self) -> ControlConfig:
        if self.target_min_f < HARD_TARGET_MIN_F or self.target_max_f > HARD_TARGET_MAX_F:
            raise ValueError(
                f"target range {self.target_min_f}-{self.target_max_f} F is outside "
                f"{HARD_TARGET_MIN_F}-{HARD_TARGET_MAX_F} F"
            )
        if self.target_min_f >= self.target_max_f:
            raise ValueError("target_min_f must be below target_max_f")
        if (
            self.hysteresis_min_f < HARD_HYSTERESIS_MIN_F
            or self.hysteresis_max_f > HARD_HYSTERESIS_MAX_F
        ):
            raise ValueError(
                f"hysteresis bounds must stay inside {HARD_HYSTERESIS_MIN_F}-{HARD_HYSTERESIS_MAX_F} F"
            )
        return self


class ProfilesConfig(_Strict):
    builtin: bool = True
    user_dir: str = "/etc/fermentd/profiles.d"
    default_profile: str = "soda_ginger_ale"
    carbonation_max_vol: float = 3.0


class DigestConfig(_Strict):
    enabled: bool = True
    weekday: str = "sunday"
    time: str = "09:00"

    @model_validator(mode="after")
    def check_schedule(self) -> DigestConfig:
        if self.weekday.lower() not in {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }:
            raise ValueError(f"unknown digest weekday {self.weekday}")
        hour, minute = self.time.split(":")
        if not (hour.isdigit() and minute.isdigit()):
            raise ValueError("digest time must be HH:MM")
        if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
            raise ValueError("digest time must be HH:MM")
        return self


class WebConfig(_Strict):
    bind: str = "127.0.0.1"
    port: int = 8080
    url: str | None = None
    # Extra origins (scheme://host[:port]) allowed to post to the dashboard, e.g. a proxy URL.
    allowed_origins: list[str] = Field(default_factory=list)
    # Serve on a public/LAN address without a login. Only for a trusted, firewalled network.
    allow_insecure: bool = False

    @model_validator(mode="after")
    def url_ok(self) -> WebConfig:
        if self.url is not None and not self.url.startswith(("http://", "https://")):
            raise ValueError("web url must start with http:// or https://")
        return self


class FermentdConfig(_Strict):
    site: SiteConfig
    database: DatabaseConfig
    one_wire: OneWireConfig
    temp_zones: list[ZoneConfig] = Field(min_length=1)
    vessels: list[VesselConfig] = Field(min_length=1)
    safety: SafetyConfig = SafetyConfig()
    control: ControlConfig = ControlConfig()
    profiles: ProfilesConfig = ProfilesConfig()
    digest: DigestConfig = DigestConfig()
    web: WebConfig = WebConfig()
    secrets: str = "/etc/fermentd/secrets.yaml"

    @model_validator(mode="after")
    def cross_check(self) -> FermentdConfig:
        zone_ids = [zone.id for zone in self.temp_zones]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("temperature zone ids must be unique")
        vessel_ids = [vessel.id for vessel in self.vessels]
        if len(vessel_ids) != len(set(vessel_ids)):
            raise ValueError("vessel ids must be unique")
        zones = set(zone_ids)
        probes: list[str] = [self.one_wire.ambient_probe]
        gpios: list[tuple[str, int]] = [("one_wire", self.one_wire.gpio)]
        for vessel in self.vessels:
            if vessel.temp_zone is not None and vessel.temp_zone not in zones:
                raise ValueError(f"vessel {vessel.id} references unknown temperature zone {vessel.temp_zone}")
            if vessel.probe_rom_id:
                probes.append(vessel.probe_rom_id)
            if vessel.scale is not None and vessel.scale.driver == "hx711":
                gpios.append((f"{vessel.id}.scale.dout", vessel.scale.dout_gpio))
                gpios.append((f"{vessel.id}.scale.sck", vessel.scale.sck_gpio))
        if len(probes) != len(set(probes)):
            raise ValueError("probe ROM ids must be unique, including the ambient probe")
        seen: dict[int, str] = {}
        for label, gpio in gpios:
            if gpio in seen:
                raise ValueError(f"GPIO {gpio} is used by both {seen[gpio]} and {label}")
            seen[gpio] = label
        for zone in self.temp_zones:
            low = self.control.target_min_f
            high = self.control.target_max_f
            if not (low <= zone.default_target_f <= high):
                raise ValueError(
                    f"zone {zone.id} default target {zone.default_target_f} F is outside {low}-{high} F"
                )
            h_low = self.control.hysteresis_min_f
            h_high = self.control.hysteresis_max_f
            if not (h_low <= zone.default_hysteresis_f <= h_high):
                raise ValueError(
                    f"zone {zone.id} hysteresis {zone.default_hysteresis_f} F is outside {h_low}-{h_high} F"
                )
        return self


class TuyaSecret(_Strict):
    device_id: str
    local_key: str


class NtfySecret(_Strict):
    topic: str
    server: str = "https://ntfy.sh"
    token: str | None = None

    @model_validator(mode="after")
    def topic_ok(self) -> NtfySecret:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.topic):
            raise ValueError("ntfy topic must be 1-64 letters, numbers, underscores, or hyphens")
        if not self.server.startswith("https://"):
            raise ValueError("ntfy server must start with https://")
        return self


class McpSecret(_Strict):
    token: str = Field(min_length=24, repr=False)


class WebSecret(_Strict):
    # scrypt$N$r$p$salt$hash, written by `fermentd-ctl set-password`.
    password_hash: str | None = Field(default=None, repr=False)
    # Optional bearer token for scripts: `Authorization: Bearer <token>`.
    token: str | None = Field(default=None, min_length=24, repr=False)
    # Optional cookie signing key; defaults to one derived from the hash and token.
    session_secret: str | None = Field(default=None, min_length=24, repr=False)

    @model_validator(mode="after")
    def hash_ok(self) -> WebSecret:
        if self.password_hash is not None:
            parts = self.password_hash.split("$")
            if len(parts) != 6 or parts[0] != "scrypt":
                raise ValueError("web password_hash must come from `fermentd-ctl set-password`")
        return self


class Secrets(_Strict):
    web: WebSecret | None = None
    tuya: dict[str, TuyaSecret] = Field(default_factory=dict)
    ntfy: NtfySecret | None = None
    mcp: McpSecret | None = None


def load_config(path: Path) -> FermentdConfig:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a mapping")
    return FermentdConfig.model_validate(raw)


def load_secrets(path: Path) -> Secrets:
    if not path.exists():
        return Secrets()
    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a mapping")
    return Secrets.model_validate(raw)


def load_actuator_secrets(path: Path) -> Secrets:
    """Plug credentials for heaters-off. A broken ntfy block must not stop the command."""
    try:
        return load_secrets(path)
    except Exception:
        return _tuya_secrets_only(path)


def _tuya_secrets_only(path: Path) -> Secrets:
    try:
        text = path.read_text()
    except OSError:
        return Secrets()
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return Secrets()
    if not isinstance(raw, dict):
        return Secrets()
    tuya = raw.get("tuya")
    if not isinstance(tuya, dict):
        return Secrets()
    try:
        return Secrets.model_validate({"tuya": tuya})
    except Exception:
        return Secrets()
