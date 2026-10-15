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

- **Public, read-only** (optional): `fermentd-mcp-public`, for cloud MCP clients such as Gemini's
  custom connector that can't reach your tailnet. See [below](#public-read-only-endpoint-oauth).

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

## Public read-only endpoint (OAuth)

Cloud MCP clients (for example Gemini's custom MCP connector) connect from the provider's servers,
not your computer, so they need a public `https://` URL and OAuth. `fermentd-mcp-public` provides
that as a separate server with a smaller attack surface:

- **Read tools only.** It is built with `build_server(read_only=True)`, which never registers a tool
  without `readOnlyHint`. The WRITE tools don't exist on it, so `tools/call` for one fails. The
  database is still opened read-only.
- **Listens on 127.0.0.1:8766**, and [Tailscale Funnel](https://tailscale.com/kb/1223/funnel) publishes
  just that port. The dashboard and the tailnet MCP server stay private.
- **OAuth 2.1 authorization server built in** (no third-party identity provider):
  - `/.well-known/oauth-protected-resource[/mcp]` (RFC 9728) and
    `/.well-known/oauth-authorization-server` (RFC 8414) metadata.
  - `/authorize`: a login + consent page that asks for the **dashboard password**
    (`web.password_hash`). Failed logins are limited to 5 per IP per 5 minutes and 20 overall per
    15 minutes.
  - `/token`: `authorization_code` with PKCE S256 (codes single-use, 5 minutes) and `refresh_token`
    (rotated on every use; reusing an old one revokes the whole chain). Access tokens last 1 hour,
    refresh tokens 30 days. A client authenticates with `client_secret_basic` or `client_secret_post`,
    or, as a public client (`none`, which is what Gemini uses), with PKCE alone.
  - `/register`: dynamic client registration (RFC 7591), which Gemini uses. A registration must use
    the allowed redirect URIs below; at most 20 per 15 minutes and 50 kept. Registering grants
    nothing by itself: every sign-in still needs the dashboard password.
  - One pre-registered client from `init-client`, for clients that take a client id and secret.
  - Codes and tokens are stored as sha256 hashes in `data/mcp-oauth.db`; the client secret is
    stored only as a sha256 in `secrets.yaml`.
  - Redirect URIs: Gemini's (`https://vertexaisearch.cloud.google.com/oauth-redirect` and
    `.../static/oauth/oauth.html`), other `https` URLs on `google.com` / `googleusercontent.com`, and
    any listed in `mcp_public.redirect_uris`. Rejected ones are logged (`journalctl -u fermentd-mcp-public`).
- An MCP request without a valid token gets `401` with
  `WWW-Authenticate: Bearer resource_metadata="<issuer>/.well-known/oauth-protected-resource/mcp"`.

### Setup

```sh
# 1. Create the OAuth client (prints the id and secret once; only the hash is stored).
.venv/bin/fermentd-mcp-public init-client --secrets config/secrets.yaml
# 2. Tell it its public URL. Use port 443 (no port in the URL): Gemini rejects other ports.
#    Funnel on 443 takes :443 on the Tailscale IP, so Caddy serves the dashboard on :8443 instead.
echo 'FERMENTD_PUBLIC_ISSUER=https://<pi>.<tailnet>.ts.net' >> config/fermentd.env
# 3. Install and start the unit.
scripts/install-units.sh && sudo systemctl enable --now fermentd-mcp-public
# 4. Publish only that port. Funnel must be allowed for the node in the tailnet policy
#    ("nodeAttrs": [{"target": ["autogroup:member"], "attr": ["funnel"]}]) and HTTPS enabled.
sudo tailscale funnel --bg --https=443 http://127.0.0.1:8766
```

In the client, use `https://<pi>.<tailnet>.ts.net/mcp` as the server URL. Gemini registers itself
(leave its client id and secret empty, or paste the `init-client` ones). Clients that ask for endpoints explicitly: authorization URL `<issuer>/authorize`, token URL
`<issuer>/token`, scope `fermentd.read`, PKCE on. If a client cannot do PKCE, set
`mcp_public.require_pkce: false` (the client secret is still required).

To turn it off: `sudo tailscale funnel --https=443 off` and `sudo systemctl disable --now fermentd-mcp-public`.
To revoke everything, delete `data/mcp-oauth.db` and restart; to replace the client, remove the
`mcp_public` block and run `init-client` again.
