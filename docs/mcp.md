# MCP server

`fermentd-mcp` lets an AI assistant read the fermentation data and, through a few clearly marked
tools, act on it.

- **stdio**: `python -m fermentd.mcp --db data/fermentd.db`, typically over SSH
  (`ssh fermentd ... -m fermentd.mcp`).
- **HTTP** (streamable HTTP): `fermentd-mcp --http --host <tailscale-ip> --port 8765 --db ... --secrets ...`.
  It binds only to the Tailscale address, and every request needs `Authorization: Bearer <token>`
  (constant-time compare). The token is `mcp.token` in `secrets.yaml`, at least 24 characters. The
  unit is `deploy/systemd/fermentd-mcp.service`; it reads the listen address (`FERMENTD_MCP_HOST`)
  from `config/fermentd.env`. Photo links use `FERMENTD_DASHBOARD_URL` (default `http://127.0.0.1:8080`).

Read tools open the database read-only (`mode=ro` plus `PRAGMA query_only`). Write tools never write
directly: they queue a command for the controller, through the same validation, safety checks and
audit log as the dashboard, with actor `mcp`. Secrets (plug keys, ntfy topic, MCP token) never appear
in any tool result. All times are America/New_York.

The server version includes a hash of the tool list, so clients that cache tools can tell when the
set changed. `scripts/deploy.sh` also ends stale stdio sessions after a deploy.

## Tools

### Read

| Tool | Returns |
|---|---|
| `list_vessels` | Enabled vessels with current batch, latest temperature, target, mat on/off |
| `get_vessel_status` | One vessel: batch, temperature, heat mat, open alerts |
| `get_vessel_temperature` | Current temperature, target, delta, room temperature, reading age |
| `get_vessel_temperature_history` | Min/max/avg per time bucket, with room average and mat % on |
| `get_vessel_heater` | Mat on/off, last change, duty cycle for 24 h and the batch, safety cutoff state |
| `get_vessel_weight` | Scale weight, CO2 lost, loss rate, estimated ABV (`has_scale=false` if none) |
| `list_batches` | Batches with vessel, profile, stage and day count |
| `get_batch` | Profile, stage schedule, current and next temperature step, upcoming reminders |
| `get_batch_gravity` | Hydrometer readings with ABV and attenuation |
| `list_alerts` | Alerts newest first, with plain-English text |
| `list_profiles` | Profile summaries: drink type, default target, allowed range, batch sizes |
| `get_profile` | Full profile with stages and guidance |
| `get_next_actions` | Current stage, the guide's next steps, pending reminders |
| `get_batch_tweaks` | "Recipe says" vs "you used" for each ingredient |
| `list_tastings` | Tasting log entries |
| `get_best_batches` | Batches ranked by tasting rating, with their tweaks |
| `list_variants` | Saved "my version" recipes usable by `start_batch` |
| `list_batch_notes` | Notes with photo links |
| `get_batch_activity` | What was done to a batch, in plain English |

### WRITE (changes state on the Pi)

| Tool | Does |
|---|---|
| `start_batch` | Start a batch on an idle vessel (optionally from a variant) and start heating |
| `advance_stage` | Move a batch to the next (or a named) stage |
| `complete_reminder` | Mark a reminder done and clear its alert |
| `log_gravity` | Log a hydrometer reading (temperature-corrected if a sample temperature is given) |
| `end_batch` | End an active batch (marked destructive) |
| `add_batch_tweak` / `remove_batch_tweak` | Record or undo a recipe change |
| `log_tasting` | Add a tasting entry |
| `save_tweaks_as_variant` | Save a batch's tweaks as a "my version" recipe |
| `add_batch_note` | Add a timestamped note |
