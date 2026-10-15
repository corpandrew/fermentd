# Security

fermentd switches a heater on and off, so treat the dashboard and the MCP server as control
surfaces, not just status pages.

## Running it safely

- **Keep it private.** Bind the dashboard to `127.0.0.1` (and put a reverse proxy such as Caddy in
  front) or to a Tailscale address. Don't port-forward it or expose it to the internet.
  `fermentd-web` refuses to start on any other address unless a login is configured, or you pass
  `--insecure-no-auth` / set `web.allow_insecure: true`.
- **Set a dashboard password.** `fermentd-ctl --config config/fermentd.yaml set-password` stores a
  scrypt hash in `secrets.yaml`. Once set, every change (POST) needs a login: a signed session
  cookie (`HttpOnly`, `SameSite=Lax`, `Secure` over https) or `Authorization: Bearer <web.token>`.
  Reading the dashboard stays open, so a private network still matters.
- **CSRF.** Every POST/PUT/PATCH/DELETE must come from the dashboard's own origin (checked with
  `Origin`, or `Referer` when `Origin` is missing). If you reach the dashboard through another URL,
  add it to `web.allowed_origins`.
- **MCP over HTTP** needs a bearer token (`mcp.token`, 24+ characters) and should listen only on a
  Tailscale address.
- **The public MCP endpoint is optional and read-only.** `fermentd-mcp-public` (behind Tailscale
  Funnel) registers no write tools, listens on 127.0.0.1 only, and needs an OAuth access token
  obtained by logging in with the dashboard password (rate limited, PKCE, rotating refresh tokens,
  one pre-registered client, redirect allowlist). Anyone on the internet can reach its login page,
  so use a strong dashboard password. Don't publish the dashboard or port 8765 with Funnel. See
  [docs/mcp.md](docs/mcp.md#public-read-only-endpoint-oauth).
- **Secrets stay local.** `config/fermentd.yaml`, `config/secrets.yaml` (mode 600),
  `config/fermentd.env`, Tuya `devices.json`/`snapshot.json`, keys and certificates are gitignored.
  The ntfy topic name is a secret: anyone who knows it can read and send your alerts.
- The control service is the only thing that touches hardware, and it keeps its own safety limits
  (hard max temperature, heater runtime caps, plug-off on start and stop) whatever the dashboard asks.

## Reporting a vulnerability

Please don't open a public issue. Use GitHub's private vulnerability reporting
(**Security → Report a vulnerability** on the repository). This is a one-person hobby project, so
expect a reply within a couple of weeks, and a fix as time allows.
