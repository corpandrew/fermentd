# Configuration reference

fermentd reads two files:

- **`fermentd.yaml`**: everything that isn't secret. Start from `config/fermentd.example.yaml`.
- **`secrets.yaml`**: plug keys, the ntfy topic and the MCP token. Mode `600`. Start from
  `config/secrets.example.yaml`. Never commit it.

Unknown keys are rejected, so typos fail loudly at startup. All values below are examples.

## fermentd.yaml

```yaml
site:
  name: basement
  timezone: America/New_York

database:
  path: data/fermentd.db
  backup_dir: data/backups
  raw_retention_days: 30

one_wire:
  gpio: 4
  sysfs_root: /sys/bus/w1/devices
  ambient_probe: 28-0000000000a1      # room probe ROM id

temp_zones:
  - id: zone1
    name: Zone 1
    capability: heat                  # heat only for now
    mode: auto                        # or test
    heater:
      driver: tuya                    # tuya | sim | none
      device_id_ref: teckin_mat       # key under tuya: in secrets.yaml
      ip: 192.168.1.50                # reserve this in your router
      protocol_version: "3.3"
      switch_dp: 1
      countdown_dp: 11                # only after a bench test; null to disable
    default_target_f: 72.0
    default_hysteresis_f: 1.0
    min_on_minutes: 5
    min_off_minutes: 5

vessels:
  - id: vessel1
    name: Vessel 1
    vessel_type: bottle_group         # jug | carboy | bucket | jar | bottle_group
    capacity_l: 3.8
    enabled: true
    temp_zone: zone1                  # null = monitor-only
    probe_rom_id: 28-0000000000b2
    # scale:                          # optional HX711 load cell
    #   driver: hx711                 # hx711 | sim | none
    #   dout_gpio: 5                  # physical pin 29
    #   sck_gpio: 6                   # physical pin 31
    #   samples: 15
    #   sample_interval_s: 300        # 30-3600

safety:
  cutoff_f: 80.0                      # can only be lowered
  cutoff_clear_f: 78.0
  max_on_minutes: 240
  rest_minutes: 15
  probe_min_f: 32.0
  probe_max_f: 120.0
  max_rate_f_per_min: 5.0
  ambient_fault_disables_heat: true
  plug_unreachable_alert_after_s: 180

control:
  target_min_f: 50.0                  # hard floor 50
  target_max_f: 75.0                  # hard ceiling 75
  hysteresis_min_f: 0.5
  hysteresis_max_f: 3.0
  over_target_margin_f: 2.0
  over_target_minutes: 120
  probe_silent_s: 120
  heater_stuck_minutes: 45
  heater_stuck_min_rise_f: 0.5
  heater_stuck_repeat_minutes: 180
  stage_change_grace_minutes: 120
  probe_settle_minutes: 10
  tuning:                             # optional, by vessel type or vessel id
    bottle_group: {window_min: 60, base_duty: 0.25, gain_per_f: 0.35}
    jug: {overshoot_f: 0.4, on_below_f: 0.6}

profiles:
  builtin: true
  user_dir: config/profiles.d
  default_profile: soda_ginger_ale
  carbonation_max_vol: 3.0

digest:
  enabled: true
  weekday: sunday
  time: "09:00"

web:
  bind: 127.0.0.1                     # loopback or a Tailscale IP; anything else needs a login
  port: 8080
  url: https://fermentd.example.com   # what a tapped notification opens; also a trusted origin
  allowed_origins: []                 # other URLs you open the dashboard through
  allow_insecure: false               # true = serve on a LAN/public address with no login (avoid)

secrets: config/secrets.yaml
```

Tuning keys (`control.tuning.<type-or-id>`): `mode` (`onoff` / `proportional`), `overshoot_f`,
`on_below_f`, `min_on_min`, `min_off_min`, `smoothing`, `window_min`, `base_duty`, `gain_per_f`,
`max_duty`, `hot_cut_f`. Defaults are in `src/fermentd/control/tuning.py` and explained in
[control-and-safety.md](control-and-safety.md).

Vessels and zone names edited on the dashboard are stored in the database and win over this file.

## secrets.yaml

```yaml
tuya:
  teckin_mat:
    device_id: "replace-with-device-id"
    local_key: "replace-with-local-key"

ntfy:                                 # optional
  topic: "replace-with-a-long-random-topic"   # 1-64 letters, numbers, _ or -
  server: "https://ntfy.sh"           # must be https
  # token: "replace-if-your-topic-needs-one"

mcp:                                  # needed for fermentd-mcp --http
  token: "replace-with-at-least-24-random-characters"

web:                                  # optional dashboard login; writes need it once set
  password_hash: "scrypt$16384$8$1$..."   # written by `fermentd-ctl set-password`
  # token: "optional-bearer-token-24+-chars"   # Authorization: Bearer <token> for scripts
  # session_secret: "optional-cookie-signing-key"   # default: derived from the hash and token
```

Changing the password (or token) signs every browser out. `config/fermentd.env` (from
`config/fermentd.example.env`) holds the MCP listen address and the photo-link base URL; it is
local to the Pi and not committed.
