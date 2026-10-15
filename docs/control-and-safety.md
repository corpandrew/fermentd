# Control logic and safety

## The control loop

`fermentd-control` runs a loop every **10 seconds**. Each pass it:

1. Reads every DS18B20 probe and checks it (in range 32–120°F, not jumping more than 5°F/min, not
   stale for more than 90 s).
2. Runs the **safety check** for each zone (below). If safety says off, the mat is off, full stop.
3. Otherwise decides on/off from the zone target and the vessel's **tuning**, and switches the plug.
4. Re-arms the plug's countdown timer if the mat is on, and checks that it really is armed.
5. Runs any queued commands from the dashboard or MCP, due reminders, scale samples, the weekly
   digest, and alert bookkeeping (open, escalate, auto-resolve).

## Per-vessel tuning

Different vessels warm very differently, so the zone is tuned for its slowest vessel type. The
defaults come from measuring the real rig (a gallon of water vs sealed bottles in the cooler) and live
in `src/fermentd/control/tuning.py`. Any value can be overridden in `fermentd.yaml` under
`control.tuning`, keyed by vessel type or vessel id.

### Jug: on/off with an early-off band

A jug warms about 3.7°F/hour and keeps rising about 0.4°F after the mat turns off. So the mat turns
**off 0.4°F below the target** and back **on 0.6°F below**, letting the leftover heat carry it to the
target. Minimum on and off times are 5 minutes, and the temperature is a **median of the last 3
readings** to ignore one-off wobbles (a real jump of more than 0.5°F, like moving the probe, passes
straight through).

### Bottles: timed bursts

Sealed bottles respond slowly (about 20 minutes of lag, 1.3°F/hour), so on/off control overshoots.
Instead, every **60-minute window** the mat gets one burst:

- **25%** of the window (15 minutes) when the bottles are right at the target,
- plus **35% per degree** below the target,
- never shorter than **15 minutes** (a burst that would be shorter is skipped, or rounded up to 15
  if it's at least half that), with at least 15 minutes off,
- ended early if the bottles get 0.3°F above the target.

In practice this is one 15-minute burst an hour that holds the bottles within about half a degree.

### Other details

- **Probe-move settling**: when a vessel's probe is moved or changed, its readings for the next
  10 minutes (`probe_settle_minutes`) are still charted but left out of stats and alerts.
- **Stage-change grace**: warnings stay quiet for 120 minutes after a stage change.
- **Planned restarts**: `fermentd-ctl planned-restart` writes a marker valid for 5 minutes before
  restarting the services, so a deploy doesn't page you. The heater is turned off on every stop and
  start (`heaters-off --all` in the systemd unit) regardless.

## Safety layers

From the outside in:

1. **Plug-in thermostat** (recommended hardware, about 78°F) between the plug and the mat.
2. **Plug countdown (Teckin DP 11)**. While the mat is on, the controller sets the plug's own
   countdown timer to **10 minutes, re-armed every 10-second cycle**. If the Pi, the controller or
   Wi-Fi dies, the plug turns itself off within 10 minutes. A **self-check** verifies the plug has
   acknowledged an arm within the last minute and doesn't report a countdown of zero; otherwise it
   raises `countdown_not_armed`. The dashboard and `get_vessel_heater` show "Safety cutoff: armed".
   Only set `countdown_dp` after a bench test shows it opens the relay (the SP10 passed one).
3. **Hard limits in code**, which config can tighten but never loosen:
   - **Over-temperature cutoff at 80°F** (or a lower profile cutoff). Any probe above it latches the
     mat off until every probe is back below 78°F for a while.
   - **Max on-time of 4 hours**, then a 15-minute rest.
   - **Probe fault lockout**: a faulted or silent probe in a zone holds its mat off (the room probe
     too, unless `ambient_fault_disables_heat: false`).
   - **Targets limited to 50–75°F**; a target outside the batch's allowed range holds the mat off.
4. **Startup and shutdown**: the heater is forced off before the service starts and after it stops.
5. **Heater watch**: the controller compares what the plug reports with what it asked for, notices
   when the plug stops answering, and notices when the mat is on but the temperature isn't rising.

## Alerts

Alerts have a severity: **info**, **warning**, **action** (needs you) or **critical**. Each condition
has one open alert at a time; if it gets worse it **escalates** to a higher severity instead of
opening a duplicate. Most clear themselves when the condition goes away, and any can be acknowledged
from the dashboard. Action and critical alerts (and the digest) are pushed to the phone.

| Type | Severity | Meaning |
|---|---|---|
| `overtemp_cutoff` | critical | A probe is above the cutoff; mat held off |
| `sensor_fault` | critical | A probe stopped reading or reads nonsense; mat held off |
| `probe_silent` | action | A vessel probe hasn't reported for 2 minutes (`probe_recovered` info push when it's back) |
| `config_conflict` | action | The target is outside the range this batch allows |
| `max_on_rest` | info | Mat was on for 4 hours, so it's resting |
| `heater_unreachable` | action, critical while heating | The plug didn't answer 3 times in a row |
| `heater_state_mismatch` | action, critical if the mat is on when it should be off | The plug didn't switch the way the controller asked |
| `heater_stuck` | action | Mat on for 45 min but the temperature rose less than 0.5°F |
| `countdown_arm_failed` | action | The plug's safety timer couldn't be set |
| `countdown_not_armed` | warning | Mat is on but the safety timer isn't set |
| `temp_below_target` | warning | 3°F or more below target for 3 hours; the mat may not be keeping up |
| `temp_out_of_range` | action | Outside the profile's range (plus 2°F) for 2 hours |
| `pressure_risk` | action | Bottles warm enough to over-pressurize; move them to the fridge |
| `reminder_due` / `refrigerate_now` | action → critical | A batch reminder is due (escalates if ignored) |
| `fermentation_slowing` | info | The scale shows fermentation slowing down |
| `fermentation_quiet` | action | Weight stable for 48 hours; probably finished |
| `target_reached` | info | The batch reached its target temperature |
| `control_fault` | critical | The control loop hit an error and turned the mat off; it keeps retrying |
| `service_stopping` | push | The control service is stopping cleanly; mat being turned off |
| `service_interrupted` | critical | fermentd crashed or lost power and restarted; clears itself after about 3 minutes of normal running |
| `pi_offline` | push | Sent by ntfy itself when the Pi misses its scheduled check-in (see below) |

## Notifications

Notifications go through a **fan-out** to every configured backend:

- **Log**: always on, written to the `fermentd` log (journald on the Pi).
- **ntfy**: optional phone push. Messages are queued in the database and delivered on a background
  thread with retries (30 s up to an hour), so a slow ntfy server never stalls temperature control.
  Tapping a push opens `web.url`.
- **Dead-man check-in**: while running, the controller keeps a delayed ntfy message scheduled about
  30 minutes ahead and keeps pushing it back. If the Pi goes quiet, that message is delivered as
  `pi_offline`.
