# Running it on the Pi

## Pi setup

Raspberry Pi OS Lite 64-bit (Bookworm or newer), Python 3.11+.

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git python3-venv python3-dev sqlite3 python3-lgpio
sudo timedatectl set-timezone America/New_York
echo 'dtoverlay=w1-gpio,gpiopin=4' | sudo tee -a /boot/firmware/config.txt
sudo reboot
```

Then clone the repo, make a venv and install:

```bash
git clone https://github.com/<you>/fermentd.git ~/fermentd
cd ~/fermentd
python3 -m venv .venv && .venv/bin/pip install -e .
cp config/fermentd.example.yaml config/fermentd.yaml
install -m 600 config/secrets.example.yaml config/secrets.yaml
.venv/bin/fermentd-ctl --config config/fermentd.yaml probes     # find your ROM ids
```

Edit `config/fermentd.yaml` (see [configuration.md](configuration.md)): real probe ROM ids, the
database path, `heater.driver: tuya`, the plug's IP, `web.bind`, and `web.url`.

### systemd units

`deploy/systemd/` has three units: `fermentd-control` (hardware + control loop), `fermentd-web`
(dashboard) and `fermentd-mcp` (MCP over HTTP), and `deploy/backup/` has the nightly backup
service and timer. They are templates for one layout: a checkout in a user's home with its own
`.venv`, `config/` and `data/`. `scripts/install-units.sh` fills in the user and the checkout path
and installs them:

```bash
cp config/fermentd.example.env config/fermentd.env   # set FERMENTD_MCP_HOST to your Tailscale IP
scripts/install-units.sh                              # DRY_RUN=1 to just print the rendered units
sudo systemctl start fermentd-control fermentd-web fermentd-mcp fermentd-backup.timer
```

`config/fermentd.env` is local to the Pi and not committed. The MCP unit reads the listen address
from it (default `127.0.0.1`), and the MCP server reads `FERMENTD_DASHBOARD_URL` for photo links.

The control unit runs `fermentd-ctl heaters-off --all` before starting and after stopping, so a
restart never leaves the mat on.

### Dashboard login

Writes on the dashboard (starting batches, changing targets, notes, etc.) need a login once a
password is set. Reads stay open, so keep the dashboard on `127.0.0.1` behind a reverse proxy or on
your tailnet either way.

```bash
.venv/bin/fermentd-ctl --config config/fermentd.yaml set-password   # stores a scrypt hash in secrets.yaml
.venv/bin/fermentd-ctl --config config/fermentd.yaml planned-restart
```

`fermentd-web` refuses to start on any address other than loopback or Tailscale without a password
or token, unless you pass `--insecure-no-auth` or set `web.allow_insecure: true`. See
[SECURITY.md](../SECURITY.md).

## Getting the Tuya local key

1. On iot.tuya.com, create a Cloud project in the same data centre as your Smart Life app, enable
   IoT Core, and link your Smart Life account so the plug shows up.
2. Run tinytuya's scan and wizard:
   ```bash
   python3 -m venv ~/tuya && ~/tuya/bin/pip install tinytuya
   ~/tuya/bin/python -m tinytuya scan
   ~/tuya/bin/python -m tinytuya wizard
   ```
3. Put the plug's `id` and `key` in `secrets.yaml` under `tuya.<name>` (`device_id`, `local_key`).
   The IP and protocol version go in `fermentd.yaml`.
4. Delete or lock down `devices.json` / `tinytuya.json`; they contain the keys. Re-pairing the plug
   in the app changes the key.
5. Check it: `fermentd-ctl plug-test zone1 --config config/fermentd.yaml`.

## Phone notifications (ntfy)

Install the ntfy app, subscribe to a long random topic, and add it to `secrets.yaml`:

```yaml
ntfy:
  topic: "replace-with-a-long-random-topic"
```

Restart `fermentd-control`. `server` defaults to `https://ntfy.sh`; add `token` if your topic needs
one. Leave the block out and nothing is pushed. See
[control-and-safety.md](control-and-safety.md#notifications) for retries and the offline check-in.

## Deploying an update

From a machine that can `ssh fermentd`:

```bash
scripts/deploy.sh            # host defaults to "fermentd", remote dir to ~/fermentd
```

It rsyncs the tree (never `config/fermentd.yaml`, `config/secrets.yaml`, `data/` or Tuya device
JSON files), reinstalls, runs `fermentd-ctl planned-restart` and checks that all three services are
active, then ends stale stdio MCP sessions on both ends.

**Planned restart**: the marker tells the controller this stop and start are intentional, so it
logs them quietly and sends no push. A crash, power loss or OOM kill leaves no marker, so those
still raise `service_interrupted`. A plain `systemctl restart` without the helper sends the
"service stopping" push but no "interrupted" alert, because the stop was clean.

## HTTPS dashboard (Caddy on Tailscale)

The dashboard can be served at `https://fermentd.example.com` (your domain), reachable only on the tailnet:

- A DNS A record points the name at the Pi's Tailscale IP.
- Caddy binds only to the Tailscale IP on :443 and :80, proxies to `127.0.0.1:8080`, and redirects
  http to https. Caddy doesn't fetch certificates itself; it reads them from `/etc/caddy/certs/`.
- The certificate is from Let's Encrypt via **acme.sh** (DNS-01, ECC), installed into
  `/etc/caddy/certs` with a Caddy reload.

**Renewal note**: a certificate issued in manual DNS mode can't be renewed by acme.sh on its own. To automate it, issue once with the Vercel DNS plugin and a Vercel API token
(`acme.sh --issue --dns dns_vercel -d fermentd.example.com --force` with `VERCEL_TOKEN` exported);
acme.sh then renews from its cron job. Until then, renew by hand before the expiry.

Files: [`deploy/https/Caddyfile`](../deploy/https/Caddyfile) and
[`deploy/https/README.md`](../deploy/https/README.md). With HTTPS in place, set `web.url` to the
https address so push notifications open it.

## Nightly backup

`deploy/backup/` has a systemd timer that runs at **03:17** every night (`Persistent=true`, so a
missed run happens at next boot). `fermentd-backup.sh` takes an online SQLite backup (safe while the
services run), runs `PRAGMA integrity_check`, gzips it to `~/fermentd-backups/fermentd-YYYYMMDD.db.gz`
and keeps the newest **14**. `FERMENTD_DB`, `FERMENTD_BACKUP_DIR` and `FERMENTD_BACKUP_KEEP`
override the defaults.

```bash
sudo cp deploy/backup/fermentd-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now fermentd-backup.timer
```

To restore: stop the services, `gunzip -c` a backup over the database file, start them again.

## Handy commands

```bash
fermentd-ctl probes                       # ROM ids and temperatures
fermentd-ctl heaters-off --all            # force every heater off
fermentd-ctl plug-test zone1              # quick plug check
fermentd-ctl scale-test --dout 5 --sck 6  # read an HX711 directly
journalctl -u fermentd-control -f         # live controller log
```
