# fermentd: Home Fermentation Monitor and Controller: Implementation Plan

> **Historical document.** This is the original plan from early October 2026. Some details changed while building it (for example the control tuning, the plug countdown, MCP write tools and the Prep stage). For how fermentd works today, see the [README](../README.md) and the other files in [docs/](.).

**Owner:** Andrew
**Status:** Draft v2 (adds beverage profiles, the weekly digest and the beverage-neutral `fermentd` naming)
**Date:** October 2026
**Companion document:** `DESIGN.md` (section numbers below refer to it)

---

## 1. Overview

The work is split into ten milestones, M0 to M8 plus M3b (beverage profiles), ordered so that the riskiest unknowns (does the Teckin plug work locally, is the scale stable) are answered before the software that depends on them is built, and so that nothing touches a real batch (cider first) until the whole system has run on a vessel of water for 48 hours.

| Milestone | Outcome | Rough effort |
|-----------|---------|--------------|
| M0 | Pi set up, 1-Wire enabled, plug proven controllable locally, scale reading raw values | 4-8 h |
| M1 | Drivers + simulators + unit tests, runnable on a laptop | 8-12 h |
| M2 | Database, control service, safety guard, command queue, systemd | 12-18 h |
| M3 | Estimator, stage and done detection, alerts, reminders | 8-12 h |
| M3b | Beverage profiles: schema, loader, validation, built-ins, profile-driven stages and reminders, per-profile simulated tests | 10-16 h |
| M4 | Web dashboard (profile-aware) | 12-18 h |
| M5 | MCP server (with profile and digest tools), API keys, rate limits, tunnel | 9-13 h |
| M6 | Grok Bot routine integration: action-needed alerts and weekly digest | 4-7 h |
| M7 | 48 h water dry run, backpack-cooler fit check and tuning | 5-7 h hands-on, 2-3 days elapsed |
| M8 | First cider batch | about 1 h brew day, 4-8 weeks elapsed |
| | **Total build effort** | **roughly 70-110 h** (was 55-90 h before profiles and the digest) |

**Naming:** the project is `fermentd` (beverage-neutral; alternatives `brewwatch`, `vesselwatch`, see DESIGN 1.1). Generic entities are *vessels* (jug, carboy, bucket, jar, bottle group), *batches*, *beverage profiles* and *temperature zones*. Cider is the default profile and the first batch.

Estimates are rough and assume evenings and weekends, with familiar Python tooling and some hardware fiddling. Hardware debugging (loose jumpers, a dead HX711) is the main source of variance.

---

## 2. Tech choices and rationale

| Area | Choice | Why |
|------|--------|-----|
| OS | Raspberry Pi OS Lite, 64-bit (Pi 3B supports it) | Headless, small; 64-bit has the best package support for tailscale/cloudflared. 32-bit also works if the card already has it. |
| Language | Python 3 (whatever the OS ships, 3.11+ on current releases) in a venv | Matches the requirement; venv avoids PEP 668 "externally managed" conflicts with system pip. |
| Packaging | `pyproject.toml`, `uv` or `pip` | Standard; `uv` is fast on a Pi but optional. |
| Config | YAML via `PyYAML`, validated with `pydantic` models | Human-editable, strict validation with clear errors on typos. |
| Profiles | YAML files (built-in package data plus `/etc/fermentd/profiles.d/`), resolved with a small deep-merge, validated with pydantic, content-hashed for versioning | Same tooling as config; profiles are data, so a new beverage needs no code. |
| DB | SQLite (stdlib `sqlite3`), WAL, hand-written SQL, numbered migration files | Zero admin, perfect for one box; an ORM is unnecessary for about 15 tables. |
| GPIO | `lgpio` (or `RPi.GPIO`, which still works on a Pi 3) | Needed to bit-bang the HX711. Keep it behind the driver so the library can be swapped. |
| HX711 | Small in-repo driver (about 100 lines) | Third-party HX711 packages vary in quality; owning the driver lets us add median filtering, retries and timing checks. |
| DS18B20 | Read sysfs (`w1_therm` kernel driver) | No library needed; kernel does the 1-Wire timing. |
| Tuya | `tinytuya` | Local Tuya protocol, includes the setup wizard. |
| Kasa (fallback) | `python-kasa` (optional extra) | Local control of TP-Link Kasa plugs. |
| Async | `asyncio` in the control service | Simple concurrency for sampler, thermostat, executor and plug IO with timeouts. |
| Web | FastAPI + Jinja2 + htmx + uPlot, served by uvicorn | Server-rendered, no JS build, light on the Pi. |
| MCP | Official Python MCP SDK (`mcp`, FastMCP), Streamable HTTP | Required; mounts as an ASGI app so auth middleware can wrap it. |
| Tunnel | Tailscale Funnel or Cloudflare Tunnel | No port forwarding; see DESIGN section 16. |
| systemd | Services with `Restart=always`, `WatchdogSec`, `ExecStopPost` heater-off | Supervision and the failsafe in one place. |
| Notify | `sdnotify` (or `systemd.daemon`) | Watchdog pings from Python. |
| Tests | `pytest`, `pytest-asyncio`, optionally `hypothesis` for estimator properties | Standard. |
| Quality | `ruff` (lint + format), `mypy` (optional strict on `control/` and `safety`) | Cheap guard rails. |

---

## 3. Repository structure

```
fermentd/
  pyproject.toml
  README.md
  docs/
    DESIGN.md
    IMPLEMENTATION_PLAN.md
  config/
    fermentd.example.yaml
    secrets.example.yaml
  src/fermentd/
    __init__.py
    config.py              # pydantic models, YAML loading, validation
    units.py               # F/C conversions, SG helpers
    profiles/
      __init__.py
      schema.py            # pydantic models for profiles (stages, done rules, reminders, carbonation)
      loader.py            # built-in + user files, extends/override merge, validation, hashing, versioning
      stages.py            # core stages, per-profile stage graph, transition checks
      builtin/
        cider.yaml
        wine.yaml          # base for wine_white / wine_red
        wine_white.yaml
        wine_red.yaml
        mead.yaml
        ale.yaml
        lager.yaml         # status: unsupported_v1, requires_capability: [cool]
        soda_ginger_beer.yaml
        kombucha.yaml
        water_kefir.yaml
    db/
      __init__.py
      connection.py        # WAL pragmas, read-only vs read-write connections
      migrations/
        0001_init.sql
        0002_alerts_reminders.sql
        0003_profiles_digest.sql
      queries.py           # shared read queries (used by web + MCP)
    drivers/
      __init__.py
      base.py              # WeightSensor, TempSensor, Actuator protocols
      hx711.py
      ds18b20.py
      actuator_tuya.py
      actuator_kasa.py
      actuator_gpio.py
      sim.py               # SimScale, SimProbe, SimHeater + thermal/fermentation model
      factory.py           # build drivers from config
    control/
      __init__.py
      service.py           # main asyncio loop, startup/shutdown sequence
      sampler.py           # reads, filtering, spike/step/off-scale detection
      thermostat.py        # bang-bang + hysteresis + learned anticipation
      safety.py            # safety guard (only ever forces OFF)
      commands.py          # command executor, validation, idempotency
      estimator.py         # SG/ABV from weight, recalibration, baseline segments
      detection.py         # rate, stage, done, stall
      alerts.py            # event -> alert rules, dedupe
      reminders.py
      retention.py         # downsampling, pruning, backups
      priming.py           # priming sugar calculator
      digest.py            # weekly digest computation
    api/
      __init__.py
      service_api.py       # shared: status, history, submit_command_and_wait
    web/
      app.py
      routes.py
      templates/           # base.html, overview.html, vessel.html, partials/...
      static/              # htmx.min.js, uPlot.iife.min.js, uPlot.min.css, app.js, app.css
    mcp_server/
      server.py            # FastMCP tools
      auth.py              # bearer key middleware, scopes
      ratelimit.py
    cli.py                 # fermentd-ctl: probes, tare, calibrate, plug-test, self-test, keys, backup
  tests/
    unit/                  # thermostat, safety, estimator, detection, commands, config, profiles
    scenarios/             # full simulated batches per profile (cider, wine, mead, ale, soda, kombucha)
    integration/           # control service with sim drivers + real SQLite
    hil/                   # hardware-in-the-loop scripts, run manually on the Pi
  deploy/
    systemd/
      fermentd-control.service
      fermentd-web.service
      fermentd-mcp.service
    nftables/fermentd.nft
    scripts/
      install.sh
      backup.sh
```

**`pyproject.toml` (sketch)**

```toml
[project]
name = "fermentd"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2",
  "pyyaml",
  "tinytuya",
  "fastapi",
  "uvicorn",
  "jinja2",
  "python-multipart",
  "mcp",
  "sdnotify",
]

[project.optional-dependencies]
pi = ["lgpio"]            # or "RPi.GPIO"
kasa = ["python-kasa"]
dev = ["pytest", "pytest-asyncio", "hypothesis", "ruff", "mypy", "httpx"]

[project.scripts]
fermentd-control = "fermentd.control.service:main"
fermentd-web = "fermentd.web.app:main"
fermentd-mcp = "fermentd.mcp_server.server:main"
fermentd-ctl = "fermentd.cli:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests/unit", "tests/integration"]
```

Version pins are deliberately left loose here; pin exact versions in a lock file once M1 works.

---

## 4. Configuration

### 4.1 `/etc/fermentd/fermentd.yaml` for v1 (one vessel)

```yaml
site:
  name: basement
  timezone: America/New_York

database:
  path: /var/lib/fermentd/fermentd.db
  backup_dir: /var/lib/fermentd/backups      # plus an off-device copy, see backup.sh
  raw_retention_days: 30

one_wire:
  gpio: 4
  ambient_probe: 28-0000000000a1          # ROM ID from `fermentd-ctl probes`

temp_zones:
  - id: zone1
    name: Backpack cooler mat
    capability: heat                       # heat in v1; cool / heat_cool reserved (DESIGN 11.6)
    heater:
      driver: tuya                         # tuya | kasa | gpio_relay | sim | none
      device_id_ref: teckin_mat            # key into secrets.yaml
      ip: 192.168.1.50                     # reserve this in the router
      protocol_version: 3.3                # from tinytuya scan
      switch_dp: 1
      countdown_dp: null                   # set to e.g. 9 only if M0 proved it works
    default_target_f: 62.0
    default_hysteresis_f: 1.0
    min_on_minutes: 5
    min_off_minutes: 5

vessels:
  - id: vessel1
    name: Vessel 1
    vessel_type: jug                       # jug | carboy | bucket | jar | bottle_group
    capacity_l: 3.8
    enabled: true
    temp_zone: zone1
    hx711:
      dout_gpio: 5
      sck_gpio: 6
      samples: 15
    probe_rom_id: 28-0000000000b2
    # Calibration lives in the DB after `calibrate`; optional seed values:
    # scale_factor: 21.84
    # tare_offset: 84213

safety:
  cutoff_f: 80.0
  cutoff_clear_f: 78.0
  max_on_minutes: 240
  rest_minutes: 15
  probe_min_f: 32.0
  probe_max_f: 120.0
  max_rate_f_per_min: 5.0
  ambient_fault_disables_heat: true
  plug_unreachable_alert_after_s: 180

control:
  target_min_f: 50.0
  target_max_f: 75.0
  hysteresis_min_f: 0.5
  hysteresis_max_f: 3.0
  over_target_margin_f: 2.0
  over_target_minutes: 120

estimator:
  default_k_points_per_gl: 1.0
  evap_g_per_day: 0.0                      # set from the M7 dry run
  k_temp_g_per_f: 0.0                      # set from the M7 dry run
  hydrometer_cal_temp_f: 60.0              # check your hydrometer
  # done-rule thresholds now come from each batch's profile

profiles:
  builtin: true                            # load the packaged profiles
  user_dir: /etc/fermentd/profiles.d       # overrides and new profiles
  default_profile: cider
  carbonation_max_vol: 3.0                 # global cap; profiles may only lower it

digest:
  enabled: true
  weekday: sunday
  time: "09:00"                            # America/New_York

web:
  bind: 0.0.0.0
  port: 8080
  allowed_subnet: 192.168.1.0/24
  write_password_ref: web_password         # optional; null = no password

mcp:
  bind: 127.0.0.1
  port: 8765
  path: /mcp

diagnostics:
  allow_override: false
```

### 4.2 Adding vessel 2

**Option A: second vessel on the same mat (zone1).** Append to `vessels:`:

```yaml
  - id: vessel2
    name: Vessel 2
    enabled: true
    temp_zone: zone1
    hx711:
      dout_gpio: 13
      sck_gpio: 19
      samples: 15
    probe_rom_id: 28-0000000000c3
```

**Option B: vessel 2 gets its own mat.** Also append to `temp_zones:` and point vessel2 at it:

```yaml
  - id: zone2
    name: Vessel 2 mat
    heater:
      driver: tuya
      device_id_ref: teckin_mat_2
      ip: 192.168.1.51
      protocol_version: 3.3
      switch_dp: 1
    default_target_f: 62.0
    default_hysteresis_f: 1.0
    min_on_minutes: 5
    min_off_minutes: 5
```

and set `temp_zone: zone2` on vessel2. Then `sudo systemctl restart fermentd-control`, and tare and calibrate vessel2 from the dashboard. No code changes.

**Option C: a timer-only vessel** (for example a group of ginger beer bottles with one probe taped to a bottle). No scale, no GPIO pair:

```yaml
  - id: bottles1
    name: Bottle group 1
    vessel_type: bottle_group
    enabled: true
    temp_zone: zone1                       # only if its profile range overlaps the zone's other batches
    hx711: null
    probe_rom_id: 28-0000000000d4
```

### 4.2b Profile override example

`/etc/fermentd/profiles.d/cider.yaml` (merged over the built-in `cider`; produces `cider` version 2 when loaded):

```yaml
id: cider
temperature:
  default_target_f: 60
carbonation:
  target_vol: 2.75
reminders:
  - {at: "start+3d", text: "Smell the airlock for sulfur; add nutrient if needed"}
```

`/etc/fermentd/profiles.d/cider_still.yaml` (a new variant):

```yaml
id: cider_still
extends: cider
name: Cider (still, dry)
carbonation:
  default: still
```

Then:

```bash
sudo -u fermentd /opt/fermentd/venv/bin/fermentd-ctl profiles validate
sudo -u fermentd /opt/fermentd/venv/bin/fermentd-ctl profiles reload    # or restart fermentd-control
fermentd-ctl profiles show cider                                        # resolved YAML and version
```

Per-batch overrides go in `start_batch(..., overrides={...})` and are limited to the whitelist in DESIGN 11.3.

### 4.3 `/etc/fermentd/secrets.yaml` (mode 600, owner `fermentd`)

```yaml
tuya:
  teckin_mat:
    device_id: "bf0123456789abcdef"
    local_key: "replace-with-local-key"
web_password: "optional"
api_key_pepper: "random-32-bytes-hex"
```

---

## 5. Setup commands (reference)

Paths and commands are for current Raspberry Pi OS (Bookworm or later). On older releases `config.txt` lives at `/boot/config.txt` instead of `/boot/firmware/config.txt`.

### 5.1 OS and basics

```bash
# Flash Raspberry Pi OS Lite (64-bit) with Raspberry Pi Imager:
# set hostname (fermentd), enable SSH with your public key, configure Wi-Fi.
# (Or reuse the existing card if it already runs a current Pi OS Lite; back it up first.)

ssh andrew@fermentd.local
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git python3-venv python3-dev sqlite3 python3-lgpio unattended-upgrades
sudo timedatectl set-timezone America/New_York
timedatectl status                 # "System clock synchronized: yes"
vcgencmd get_throttled             # 0x0 means no under-voltage (check with load later)
```

### 5.2 Enable 1-Wire on GPIO4

```bash
sudo raspi-config                  # Interface Options -> 1-Wire -> Enable
# or add this line to /boot/firmware/config.txt:
#   dtoverlay=w1-gpio,gpiopin=4
sudo reboot

ls /sys/bus/w1/devices/            # expect 28-xxxxxxxxxxxx entries and w1_bus_master1
cat /sys/bus/w1/devices/28-*/temperature   # millidegrees C, e.g. 18562
```

### 5.3 Service user and directories

> Historical. The shipped units use a checkout in the user's home; see [operations.md](operations.md).

```bash
sudo useradd --system --home /var/lib/fermentd --create-home --groups gpio fermentd
sudo mkdir -p /etc/fermentd /opt/fermentd
sudo chown fermentd:fermentd /var/lib/fermentd
sudo git clone <your repo> /opt/fermentd/app
sudo python3 -m venv /opt/fermentd/venv
sudo /opt/fermentd/venv/bin/pip install -e "/opt/fermentd/app[pi]"
sudo cp /opt/fermentd/app/config/fermentd.example.yaml /etc/fermentd/fermentd.yaml
sudo install -m 600 -o fermentd -g fermentd /opt/fermentd/app/config/secrets.example.yaml /etc/fermentd/secrets.yaml
```

### 5.4 Tuya local key with tinytuya

Do this on the Pi or on a laptop (the laptop is fine; only the resulting device ID, IP and local key are needed on the Pi).

1. In the Tuya IoT Platform (iot.tuya.com), create a Cloud project. Pick the **data center that matches your Smart Life app region** (for the US, typically "Western America"). Make sure the IoT Core and Authorization API services are enabled for the project (the free trial of IoT Core may need periodic renewal; uncertain, check the console).
2. In the project, link your Smart Life app account (Devices -> Link App Account, scan the QR code with the Smart Life app). The Teckin plug should appear in the device list.
3. Note the project's Access ID and Access Secret.
4. Run the wizard:

```bash
python3 -m venv ~/tuya && ~/tuya/bin/pip install tinytuya
~/tuya/bin/python -m tinytuya scan      # finds plugs on the LAN, shows IP and protocol version
~/tuya/bin/python -m tinytuya wizard    # asks for Access ID/Secret/region, writes devices.json with local keys
```

5. Copy the plug's `id` and `key` into `/etc/fermentd/secrets.yaml`, then delete or protect `devices.json` and `tinytuya.json` (they contain secrets).
6. If the plug is ever removed and re-paired in the app, its local key changes; re-run the wizard.

**Local control test (the M0 gate):**

```python
import time, tinytuya
d = tinytuya.OutletDevice("DEVICE_ID", "192.168.1.50", "LOCAL_KEY", version=3.3)
print(d.status())               # expect {'dps': {'1': False, ...}}
d.turn_on();  time.sleep(2); print(d.status())
d.turn_off(); time.sleep(2); print(d.status())
# Countdown test (only if the status shows a countdown-like DP, often '9'):
d.turn_on(); d.set_value(9, 60) # expect the relay to switch off by itself after ~60 s
```

If `status()` returns an error (for example a protocol or decryption error) for every protocol version (3.1, 3.3, 3.4, 3.5), the plug's firmware probably does not allow local control. Fall back to Kasa (`pip install python-kasa`, `kasa discover`) or the Digital Loggers IoT Relay on GPIO18.

### 5.5 Tunnel (pick one)

**Tailscale Funnel**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Enable Funnel for this node in the Tailscale admin console (policy file), then:
sudo tailscale funnel --bg 8765
tailscale funnel status          # shows the public https://fermentd.<tailnet>.ts.net URL
```

The Funnel CLI syntax has changed across Tailscale versions; check `tailscale funnel --help` (uncertain).

**Cloudflare Tunnel** (needs a domain on Cloudflare)

```bash
# install cloudflared from Cloudflare's apt repository (see their docs for the arm64 package)
cloudflared tunnel login
cloudflared tunnel create fermentd
# /etc/cloudflared/config.yml:
#   tunnel: <tunnel-id>
#   credentials-file: /etc/cloudflared/<tunnel-id>.json
#   ingress:
#     - hostname: fermentd-mcp.example.com
#       path: ^/mcp
#       service: http://127.0.0.1:8765
#     - service: http_status:404
cloudflared tunnel route dns fermentd fermentd-mcp.example.com
sudo cloudflared service install
```

### 5.6 systemd units

`/etc/systemd/system/fermentd-control.service`

```ini
[Unit]
Description=fermentd control service (hardware, control loop, safety)
After=network-online.target time-sync.target
Wants=network-online.target

[Service]
Type=notify
User=fermentd
Group=fermentd
SupplementaryGroups=gpio
ExecStartPre=/opt/fermentd/venv/bin/fermentd-ctl heaters-off --all --config /etc/fermentd/fermentd.yaml
ExecStart=/opt/fermentd/venv/bin/fermentd-control --config /etc/fermentd/fermentd.yaml
ExecStopPost=/opt/fermentd/venv/bin/fermentd-ctl heaters-off --all --config /etc/fermentd/fermentd.yaml
Restart=always
RestartSec=5
StartLimitIntervalSec=600
StartLimitBurst=5
WatchdogSec=60
NotifyAccess=main

[Install]
WantedBy=multi-user.target
```

Note: `After=time-sync.target` only orders the start; the service must not block heating or safety on clock sync (it uses monotonic time and flags readings until synced).

`/etc/systemd/system/fermentd-web.service`

```ini
[Unit]
Description=fermentd dashboard (LAN)
After=fermentd-control.service

[Service]
User=fermentd
Group=fermentd
ExecStart=/opt/fermentd/venv/bin/fermentd-web --config /etc/fermentd/fermentd.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/fermentd-mcp.service` is the same shape with `ExecStart=/opt/fermentd/venv/bin/fermentd-mcp --config /etc/fermentd/fermentd.yaml`.

Hardware watchdog (reboots the Pi if the kernel or userspace hangs): in `/etc/systemd/system.conf` set

```ini
RuntimeWatchdogSec=15
```

then

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fermentd-control fermentd-web fermentd-mcp
journalctl -u fermentd-control -f
```

### 5.7 Firewall (LAN only for the dashboard)

```bash
sudo apt install -y nftables
# deploy/nftables/fermentd.nft: allow 22 and 8080 from 192.168.1.0/24 only; 8765 only from loopback
sudo nft -f /opt/fermentd/app/deploy/nftables/fermentd.nft
sudo systemctl enable nftables
```

### 5.8 SD card care and backups

```bash
# journald: cap size (or Storage=volatile) in /etc/systemd/journald.conf
#   SystemMaxUse=50M
sudo dphys-swapfile swapoff && sudo systemctl disable dphys-swapfile   # if present; no swap on SD
# nightly backup (cron or systemd timer), see deploy/scripts/backup.sh:
sqlite3 /var/lib/fermentd/fermentd.db "VACUUM INTO '/var/lib/fermentd/backups/fermentd-$(date +%F).db'"
# then rsync the backups directory to a USB stick, laptop or NAS, keep 14 days
```

---

## 6. Milestones

### M0: Bench setup, Pi OS, 1-Wire, plug test, raw scale

**Tasks**
- [ ] Order the remaining materials (section 8).
- [ ] Flash or update Pi OS Lite, SSH with keys, hostname `fermentd`, timezone, updates.
- [ ] Check power: `vcgencmd get_throttled` returns `0x0` under load.
- [ ] Reserve DHCP addresses for the Pi and the Teckin plug on the router.
- [ ] Enable 1-Wire on GPIO4; wire the 4.7k pull-up and two DS18B20s on the breadboard; confirm both appear in `/sys/bus/w1/devices`.
- [ ] Tuya IoT project, link Smart Life account, run `tinytuya scan` and `wizard`.
- [ ] **Gate:** local on/off/status works reliably 20 times in a row; record protocol version. Check for a countdown DP and test it with the Pi network cable/Wi-Fi disconnected mid-countdown (the relay must still switch off).
- [ ] Set the plug's power-on state to OFF in the Smart Life app if the option exists.
- [ ] If the gate fails: decide on Kasa or the Digital Loggers relay; order it.
- [ ] Build the scale platform; wire HX711 at 3.3 V to GPIO5/6; read raw values with a 20-line script; confirm the value changes in the right direction with a load.

**Acceptance criteria**
- Both probes read plausible temperatures; warming one in your hand moves only that one.
- The plug toggles locally and reports state; decision recorded on countdown DP availability.
- Raw HX711 values are stable (noise under about 0.1% of a 5 kg load) and respond linearly to two different weights.

**Tests:** manual, recorded in `docs/bench-notes.md`.

### M1: Drivers, simulators, unit tests

**Tasks**
- [ ] `config.py`: pydantic models for the YAML in section 4; unknown keys are errors; cross-checks (unique GPIOs, every vessel's zone exists, no pin collision with 1-Wire, `hx711: null` allowed for timer-only vessels).
- [ ] `drivers/base.py`: `WeightSensor`, `TempSensor`, `Actuator` protocols (DESIGN 7.2); zone `capability` field validated (only `heat` accepted in v1).
- [ ] `hx711.py`: bit-bang read with timing check, 24-bit two's complement, retry on bad reads, median of N, power-down/up.
- [ ] `ds18b20.py`: sysfs read, CRC check, 85 C and sentinel rejection, plausibility, bulk conversion if available.
- [ ] `actuator_tuya.py`: `set`, `read_state`, timeouts (2-3 s), reconnects, optional countdown arm.
- [ ] `actuator_kasa.py`, `actuator_gpio.py` (fallbacks, can be stubs with tests until needed).
- [ ] `sim.py`: thermal model (`dT/dt = (T_amb - T)/tau + heater_gain * on`, plus fermentation heat), fermentation weight model (logistic CO2 curve from OG to FG with lag), noise, injected faults (probe dropout, 85 C glitch, plug unreachable, stuck-on plug, vessel removal, step).
- [ ] `cli.py` first commands: `probes`, `read-scale`, `plug-test`, `heaters-off`.
- [ ] Unit tests for every driver against fakes (fake sysfs directory, fake GPIO, fake tinytuya device).

**Acceptance criteria**
- `pytest` passes on a laptop without any Pi hardware.
- On the Pi, `fermentd-ctl probes`, `read-scale vessel1` and `plug-test zone1` work against real hardware.
- Config validation rejects a duplicate GPIO and an unknown zone with readable messages.

**Test plan:** unit tests with fake GPIO and fake sysfs; HIL script `tests/hil/test_drivers.py` run manually on the Pi.

### M2: Database, control service, safety guard, command queue, systemd

**Tasks**
- [ ] Schema migrations (DESIGN 9) with a migration runner; WAL and pragmas. Include `BEVERAGE_PROFILE`, the batch profile columns and `DIGEST_LOG` from the start (cheap now, avoids a migration later); M2 runs with a single hard-coded `cider` profile stub until M3b.
- [ ] Config-to-DB sync for vessels and zones (upsert; disable removed).
- [ ] Control service main loop (asyncio): sampler, thermostat evaluation, safety evaluation, reading writer, plug verify, watchdog ping.
- [ ] Sampler: median, spike filter, pending window, step and vessel-off-scale detection.
- [ ] Thermostat: hysteresis, min on/off, learned anticipation with persistence.
- [ ] Safety guard as a separate module with its own tests: cutoff with latch, sensor fault, max-on and rest, unreachable, mismatch, startup and shutdown off.
- [ ] Command executor: poll, validate, idempotency, execute, audit, result; expiry.
- [ ] Commands: `set_target_temp`, `tare_scale`, `calibrate_scale`, `self_test`, `override_relay` (gated), `heaters_off`.
- [ ] Events and audit writing.
- [ ] Retention job (downsample, prune) and nightly backup.
- [ ] systemd units, `ExecStopPost`, hardware watchdog, install script.
- [ ] CLI: `tare`, `calibrate`, `self-test`, `status`.

**Acceptance criteria**
- With sim drivers, a 7-day simulated run (time-accelerated) holds the target within plus or minus 1 F of the hysteresis band after anticipation is learned, with no safety violations.
- Every safety rule in DESIGN 8.4 has a test that injects the fault and asserts the heater is commanded OFF within one evaluation tick (10 s) and the right alert is raised.
- `set_target_temp(80)` is rejected with `OUT_OF_RANGE` and the allowed range; the DB value is unchanged.
- `kill -9` of the control service on the Pi leaves the plug OFF within 10 s (via `ExecStopPost` and restart).
- Pulling power from the Pi and restoring it: the service starts, heater verified OFF before the first control decision, readings resume.

**Test plan**
- Unit: thermostat transitions (table-driven), anticipation learning, each safety rule, idempotency, validation ranges at boundaries (50, 75, 0.5, 3 accepted; 49.9, 75.1, 0.4, 3.1 rejected).
- Integration: control service + sim drivers + temp SQLite, accelerated clock.
- HIL: real plug with a lamp instead of the mat for visible feedback; unplug Wi-Fi router for 5 minutes; confirm `heater_unreachable` alert and correct re-assertion afterwards.

### M3: Estimator, stage and done detection, alerts, reminders

**Tasks**
- [ ] `estimator.py`: volume, `dm`, drift correction, `SG_est`, `ABV_est`, error band, baseline segments, `record_gravity` recalibration with bounds (DESIGN 10).
- [ ] Hydrometer temperature correction function.
- [ ] `detection.py`: hourly medians, 24 h regression rate, lag->active, active->slowing, done candidate, stalls.
- [ ] Commands: `start_batch`, `record_gravity`, `rebaseline`, `set_stage` (state machine), `add_note`, `end_batch`, `abort_batch`, `ack_alert`, `create_reminder`, `complete_reminder`.
- [ ] `alerts.py`: rules from the DESIGN 15.2 catalog, dedupe keys, escalation, auto-resolve.
- [ ] `reminders.py`: reminder engine with anchors (`start+`, `stage:`, `packaged+`), repeats; cider templates first (generalized in M3b).
- [ ] `priming.py`: residual CO2 and sugar calculator.

**Acceptance criteria**
- On a simulated fermentation (OG 1.050 to 0.998, 3.6 L) the estimate tracks the simulated truth within 0.002 after one simulated manual reading.
- Simulated hydrometer sample removal (120 g step) does not produce a jump in `SG_est` once classified.
- Done candidate fires on the simulated curve within a day of the simulated rate crossing the threshold for 3 days; not before.
- Stall alerts fire at 48 h and 72 h on a no-fermentation simulation.
- Priming calculator matches the DESIGN 12.7 table within 0.5 g.

**Test plan:** unit tests with known inputs (worked example from DESIGN 10.2), property tests (estimate is monotonic in weight loss; recalibration makes the estimate equal the manual reading at that instant), scenario tests with the fermentation simulator including vessel removal and re-placement.

### M3b: Beverage profiles

Generalizes the cider-only behaviour from M2-M3 into profile data (DESIGN 11).

**Tasks**
- [ ] `profiles/schema.py`: pydantic models for every profile field (temperature, capability, tracking mode, stages with core mapping and attributes, gravity, ABV formula, done rule, carbonation, packaging, guidance, reminders, alerts, safety tightenings).
- [ ] `profiles/loader.py`: load built-ins and `/etc/fermentd/profiles.d/`, resolve `extends` (deep merge; lists merged by `id`), apply same-id overrides, validate, hash, write new `BEVERAGE_PROFILE` versions, keep the last good set on failure (`profile_reload_failed` alert).
- [ ] Validation rules: allowed target range inside global limits; default inside allowed; safety values only tighten; `max_vol` at or below the global cap; stage graph reaches `done` from `prep`; reminder anchors refer to existing stages; capabilities known.
- [ ] `profiles/stages.py`: core stages, transition checks per profile, `requires` guards, `auto` stages wired to `detection.py`.
- [ ] Refactor `detection.py` to the three done rules (`absolute_and_plateau`, `plateau`, `timer`) with profile thresholds; per-stage `tracking` override and estimator `confidence` (low-confidence stages widen the band).
- [ ] `high_gravity` ABV formula; profile-selected.
- [ ] Reminder anchors `sg_drop_fraction` and `sg_below` (mead 1/3 sugar break), `repeat` (refrigerate-now).
- [ ] Timer mode: vessels without a scale, elapsed-time `advance_after` suggestions, `refrigerate_now` and `pressure_risk` alerts.
- [ ] `start_batch`: `profile` (default `cider`), `overrides` whitelist, capability check (`PROFILE_UNSUPPORTED` for lager on a heat-only zone), zone range-overlap check, profile snapshot; `record_addition`; `end_batch` still or sparkling per profile.
- [ ] `set_target_temp`: allowed range = global intersected with every active batch's profile range in the zone.
- [ ] Write the built-in YAML files: `cider`, `wine` + `wine_white` + `wine_red` (experimental), `mead`, `ale`, `lager` (`unsupported_v1`), `soda_ginger_beer`, `kombucha`, `water_kefir` (experimental). Mark uncertain defaults with a comment in each file.
- [ ] CLI: `fermentd-ctl profiles list|show|validate|reload|diff`.
- [ ] Extend `sim.py` with per-profile fermentation models: wine/mead (high OG, long tail), ale (FG plateau at 1.010-1.014, blow-off mass loss option), in-bottle soda (pressure proxy over time), kombucha (no weight signal, evaporation only).

**Acceptance criteria**
- All built-in profiles load and validate; a deliberately broken user file (target range 45-85, `max_vol` 4.0, unknown stage anchor) is rejected with one readable error per problem, and the previous good set stays active.
- Editing a profile does not change a running batch (snapshot test); a new version appears in `BEVERAGE_PROFILE`.
- `start_batch(profile="lager")` on the heat-only zone returns `PROFILE_UNSUPPORTED` with the cooling reason.
- `start_batch(profile="kombucha")` in a zone with an active cider batch is rejected for non-overlapping ranges.
- `set_target_temp(70)` on a zone with an active cider batch whose profile allows 55-70 succeeds; 71 fails naming the cider profile limit.
- Per-profile scenario results (simulated):
  - **cider:** done candidate near 0.998; behaviour identical to M3 (regression suite unchanged).
  - **wine_white / mead:** high-gravity ABV within 0.3% of the reference formula; rack and SNA reminders fire at the right anchors, including the 1/3 sugar break.
  - **ale:** plateau done fires with FG 1.012 (no absolute target); blow-off mass loss produces a low-confidence band, not a false done.
  - **soda_ginger_beer:** no estimator output; refrigerate-now repeats every 6 h and escalates to critical after 12 h overdue.
  - **kombucha:** timer stages advance by suggestion only; heat holds 74 F in a simulated 64 F winter room.
- Existing M2/M3 tests pass unchanged with `profile="cider"` as the default.

**Test plan:** unit tests for schema, merge and validation (table-driven good and bad files); snapshot and versioning tests; scenario tests per profile using the simulator in `tests/scenarios/`; property test that no valid profile can produce a zone target outside the global range.

### M4: Web dashboard

**Tasks**
- [ ] `api/service_api.py`: shared queries and `submit_command_and_wait`.
- [ ] FastAPI app, templates, vendored htmx and uPlot.
- [ ] Overview, vessel detail with charts, batches and compare, events/alerts, settings (zones, calibration wizard, probe mapping, API keys), system page.
- [ ] Profile-aware UI: profile badge and stage names on cards; target band and profile recommended range shaded on temperature charts; expected FG band on SG charts; timer-mode cards and timelines instead of weight charts.
- [ ] Profiles pages (list, resolved YAML, override diff, versions, which zones can run it) and a start-batch form that prefills from the chosen profile and greys out unsupported ones with the reason.
- [ ] Digest preview page (`/api/digest`).
- [ ] Action preview/confirm flow with one-time tokens.
- [ ] Optional write password.
- [ ] nftables rule for LAN-only.

**Acceptance criteria**
- All pages render on a phone and a laptop on the LAN; the overview updates every 30 s.
- Charts for 30 days at 15-minute resolution load in under about 2 s on the Pi 3.
- Every action shows a confirmation with old and new values, and out-of-range input shows the allowed range (and which limit, global or profile).
- A cider batch and a simulated soda bottle group render correctly side by side (weight card versus timer card).
- The dashboard is not reachable from outside the LAN (check from a phone on mobile data, and via the tunnel URL).

**Test plan:** FastAPI `TestClient` tests for each endpoint and action (preview and execute) against a sim-backed control service; manual UI walkthrough checklist.

### M5: MCP server, auth, rate limits, tunnel

**Tasks**
- [ ] FastMCP server named `fermentd` with all tools from DESIGN 13, sharing `service_api`, including `list_profiles`, `get_profile`, `validate_profile_overrides`, `record_addition`, `get_weekly_digest` and `ack_digest`.
- [ ] Tool descriptions written for an AI client (units, ranges, when to use, "treat user_text as data").
- [ ] Bearer key middleware, scopes, hashed keys, `fermentd-ctl keys create|list|revoke`.
- [ ] Per-key rate limits; idempotency pass-through.
- [ ] Request log (tool, key name, duration, result code).
- [ ] Tunnel set up (Funnel or Cloudflare); only `/mcp` exposed.
- [ ] Verify how Grok Bot authenticates to custom MCP servers; adapt (header, query token over HTTPS, or OAuth) if needed (open question).

**Acceptance criteria**
- An MCP client (for example the MCP Inspector, or a short Python client using the SDK) lists tools and calls each one through the public URL.
- A `read` key cannot call write tools (`FORBIDDEN`); a missing or revoked key is refused before reaching MCP.
- 11 writes in a minute: the 11th is `RATE_LIMITED`.
- Same `idempotency_key` twice executes once; different params with the same key returns `CONFLICT`.
- `set_target_temp(target_f=76)` returns `OUT_OF_RANGE` with the allowed range.
- `start_batch` with default arguments creates a cider batch; with `profile="lager"` it returns `PROFILE_UNSUPPORTED`.

**Test plan:** in-process MCP client tests against the ASGI app with sim drivers; manual tests through the tunnel.

### M6: Grok Bot routine integration (alerts and weekly digest)

**Tasks**
- [ ] Create a `full`-scope key named `grok` and connect the MCP server to Grok Bot.
- [ ] Write the routine instructions (DESIGN 15.1): every 6 h, call status, alerts, reminders, analysis; message only when needed; ack reported alerts; report unreachable after two consecutive failures.
- [ ] `control/digest.py`: compute the weekly digest (DESIGN 15.3): health line, per-batch progress (SG/ABV now versus a week ago, trend, projection labelled as such), temperature stability (mean, min, max, percent in band, largest excursion, heater duty), additions and notes, timer-mode next actions, conditioning batches, upcoming reminders for 7 days, open and resolved alerts, finished batches.
- [ ] `DIGEST_LOG` dedupe by ISO week; late digest if a week was missed.
- [ ] Routine step 8: at the first run at or after Sunday 09:00 ET, fetch the digest, send it if not already sent, then `ack_digest`. Action-needed items, if any, go first in the same message.
- [ ] Message template for the digest (short, about 5 lines per batch, single health line when nothing is active).
- [ ] Fire drills: inject a `done_candidate`, a `sensor_fault` and an unreachable server (stop the tunnel) and confirm the messages.

**Acceptance criteria**
- Silent when everything is normal for 24 h.
- Each drill produces exactly one clear message, and no repeat at the next check (except critical alerts after 24 h).
- A forced digest run sends exactly one digest per ISO week, even if the routine is triggered twice; the numbers match the dashboard for the same period.
- A week with no active batches produces a single health-line digest.

**Test plan:** fire drills using `fermentd-ctl inject-event` (dev-only command) on the Pi, or the simulator running behind a test key. Digest: unit tests over a simulated week of data (stable cider, a temperature excursion, a timer-mode batch, a finished batch); `fermentd-ctl digest preview --week 2026-W42` to eyeball the message.

### M7: 48 h water dry run and backpack-cooler fit check

Set up exactly as for a real batch, with water instead of juice: vessel filled to the shoulder with water, stopper and airlock, probe taped with foam, in the cooler, on the scale, mat in its final position. Start a test batch (`mode: test`, so heating is allowed without a "real" batch).

**Tasks**
- [ ] **Backpack cooler fit:** measure interior height against platform + jug + stopper + airlock; note whether the lid closes, needs to stay cracked, or needs a notch or zip gap for the airlock and cables. Put a rigid board under the platform if the cooler floor flexes. Record the result in `docs/bench-notes.md`.
- [ ] Weigh the empty vessel, start a test batch, target about 5 F above the room.
- [ ] Put a calibrated kitchen thermometer (or a second probe) in the water through the airlock hole for part of the run to compare liquid temperature with the outside probe (then restore the airlock).
- [ ] Run 48 h hands-off; review charts.
- [ ] Measure: weight drift per day (evaporation plus creep) to set `evap_g_per_day`; correlation of weight with ambient/mat cycling to set `k_temp_g_per_f`; overshoot learned; duty cycle; temperature band achieved.
- [ ] **Stuck-on test (supervised):** use `override_relay` (temporarily enabled) or the Smart Life app to hold the mat on, with the safety guard watching, and measure how fast the water warms. Stop at 75 F. Extrapolate the time to 80 F and the likely equilibrium. Repeat with the Pi's Wi-Fi disconnected if a countdown DP is used, to confirm the plug turns itself off.
- [ ] Failure drills: pull a probe (expect heater off + critical); unplug the plug from the wall (expect unreachable alert); reboot the Pi mid-heat (expect heater off then resume); lift the vessel off for 10 minutes and put it back (expect auto-resume); take a 120 g "sample" (expect `weight_step` and classification prompt); `record_gravity(1.000)` on water to exercise the recalibration path.
- [ ] Disable `allow_override` again.

**Acceptance criteria**
- Water temperature (per the reference thermometer) held within about plus or minus 1 F of target after the first few hours.
- Outside probe within about 1 F of the in-water reference in steady state (otherwise note an offset).
- Weight drift after compensation under about 2 g/day (otherwise investigate cable routing, mat placement, creep).
- All failure drills behave as designed, with the right alerts and Grok Bot messages.
- No safety violation; the stuck-on extrapolation is documented and acceptable (or the hardware backstop is added).
- The cooler arrangement (lid closed, cracked or notched) is decided and the cables do not visibly tug on the scale (weight steady while gently moving the cooler lid).

### M8: First cider batch

**Tasks**
- [ ] Buy juice (check label: no sorbate, no benzoate), yeast, optional nutrient and pectic enzyme.
- [ ] Run `self_test`; clean and sanitize.
- [ ] Follow DESIGN 12.3 brew-day steps; start the batch with `profile=cider` (the default) and target 62 F.
- [ ] Daily airlock glance for the first 3 days; respond to alerts.
- [ ] Optional mid-fermentation hydrometer reading around day 5-7 to calibrate `k`.
- [ ] On `done_candidate`, two readings 2-3 days apart.
- [ ] Clear 1-3 weeks (optional racking).
- [ ] Bottle with the priming calculator (target 2.5-2.75 vol), PET test bottle, `end_batch`.
- [ ] Bottle-condition with reminders; refrigerate when carbonated; `set_stage finished`.
- [ ] Review the batch summary; note what to change; update estimator priors and, if needed, the `cider` profile via an override file.

**Acceptance criteria**
- A drinkable, dry, sparkling cider with no bottle failures.
- A complete batch record: OG, FG, ABV, curves, notes, alerts, and a comparison of estimated versus measured FG.
- A short retro written in the batch notes (what alerted well, what was noise).

---

## 7. Test strategy summary

| Level | Where | What | When |
|-------|-------|------|------|
| Unit | Laptop and CI | Config validation, drivers against fakes, thermostat, safety rules, estimator math, detection, commands, priming, profile schema/merge/validation, digest | Every change |
| Integration | Laptop | Control service + sim drivers + SQLite, accelerated time; web and MCP against the same | Every change |
| Scenario | Laptop | Full simulated batches per profile (cider, wine, mead, ale, soda, kombucha) with injected faults (dropout, stuck plug, Wi-Fi loss, vessel removal, samples, blow-off loss) | Before each milestone sign-off |
| HIL | Pi on the bench | Real probes, scale and plug (with a lamp); failure drills | M1, M2, M5 |
| Dry run | Pi in the cooler | 48 h water batch, stuck-on test, failure drills | M7 |
| Live | Real batch | First cider | M8 |

The safety guard gets the most tests: every rule, its clearing condition, its interaction with minimum on/off times, overrides and restarts.

---

## 8. Bill of remaining materials (1-vessel v1)

No prices are listed on purpose; check current listings.

**Already owned:** Raspberry Pi 3B, microSD card, power supply, breadboard, seedling heat mat, Teckin smart plugs, one 1-gallon glass jug, airlock and #6 stopper, auto-siphon, bottle filler, Star San.

**Needed for the electronics**

| Item | Qty | Notes |
|------|-----|-------|
| 10 kg straight-bar load cell + HX711 board kit | 1 (buy 2 if planning vessel 2) | Kits often include mounting screws and sometimes platform plates |
| Scale platform boards (plywood or MDF, about 20 x 20 cm, 12-18 mm) plus bolts and spacers matching the load cell holes | 2 boards | Often M4 or M5 bolts; check the cell |
| DS18B20 waterproof probes | 2 (a 5-pack is common and gives spares) | Some kits include the 4.7k resistor or a small adapter board with it |
| 4.7 kOhm resistor | 1 | If not included |
| Jumper wires (female-female and male-female) | 1 pack | Consider screw-terminal blocks or soldered connections for the final install; jumpers work loose |
| Foam or closed-cell insulation patch, tape (foil tape or electrical tape) | small | For the vessel probe |
| Backpack cooler (chamber) | 1 | Owned; fit checked in M7. A small rigid board for under the platform may be needed |

**Needed for brewing**

| Item | Qty | Notes |
|------|-----|-------|
| Hydrometer and test jar | 1 | Note its calibration temperature |
| 16 oz swing-top bottles, brewing grade | 8 (plus a couple spare) | Thick glass, good gaskets |
| Small PET plastic bottle | 1 | Carbonation test bottle |
| Wine thief or turkey baster | 1 | Optional but makes sampling a 1-gallon jug much easier |

**Consumables per batch:** juice (about 1 gallon, preservative-free), yeast (champagne or cider yeast), optional yeast nutrient and pectic enzyme, priming sugar, cleaner (unscented oxygen cleaner or brewery cleaner).

**Optional or conditional**

| Item | When |
|------|------|
| Independent plug-in thermostat controller for the mat | Recommended if the plug has no countdown DP |
| Kasa smart plug or Digital Loggers IoT Relay | If the Teckin fails the local-control test |
| Second 1-gallon jug | For racking, or batch 2 |
| 2-hole #6 stopper + thermowell | For a more accurate in-liquid temperature later |
| Kitchen scale with 0.1 g resolution | For weighing priming sugar accurately |
| Second microSD card or USB stick | Backups and a spare system image |
| Blow-off tube (to fit the #6 stopper) and a small jar | Before an ale (or a vigorous mead) |
| Extra DS18B20 probe and a second mat + plug | For a second temperature zone (for example kombucha at 74 F alongside cider) |
| Small fridge or chest freezer on its own plug or relay | Only if lager (cooling zone) is pursued later |

---

## 9. Uncertainties to resolve during the build

| Item | Resolve in |
|------|-----------|
| Teckin local control works with this firmware | M0 |
| Teckin plug exposes a working countdown DP | M0 |
| HX711 read reliability from Python on the Pi 3 | M0-M1 |
| Load cell creep and temperature drift magnitude | M7 |
| Outside-probe offset versus liquid | M7 |
| Evaporation rate through the airlock | M7 |
| Time to overheat with the mat stuck on | M7 |
| Grok Bot MCP auth mechanism | M5 |
| Exact Tailscale Funnel / cloudflared commands for current versions | M5 |
| Real fermentation curve shape and the best done threshold | M8 |
| Backpack cooler fit with airlock (lid closed or not) | M7 |
| Built-in profile defaults for beverages not yet brewed (wine, mead, ale, soda, kombucha, kefir) | First batch of each |
| Final project name availability (`fermentd`, fallback `brewwatch`) | Before creating the repo |

---

## 10. Effort summary

Profiles add about 10-16 h (M3b) plus a few hours spread across M4-M6; the weekly digest adds about 2-3 h to M6.

| Milestone | Hands-on | Elapsed |
|-----------|----------|---------|
| M0 | 4-8 h | 1 weekend plus shipping time |
| M1 | 8-12 h | 1 week of evenings |
| M2 | 12-18 h | 1-2 weeks |
| M3 | 8-12 h | 1 week |
| M3b | 10-16 h | 1-2 weeks |
| M4 | 12-18 h | 1-2 weeks |
| M5 | 9-13 h | 1 week |
| M6 | 4-7 h | 1-2 evenings |
| M7 | 5-7 h | 2-3 days |
| M8 | a few hours spread out | 4-8 weeks (fermentation, clearing, conditioning) |
| **Total** | **roughly 70-110 h** | |

A shortcut if you want cider sooner: after M2 (control and safety working) and a shortened M7, the first (cider) batch can start while M3-M6 are built (M3b can wait until after the first batch, since cider is the hard-coded default until then), because the control service already logs weight and temperature; the batch record (OG, start time, start weight) can be entered when M3 lands and the estimate computed retroactively from the logged readings. Only do this if the safety guard tests and the dry-run failure drills have passed.
