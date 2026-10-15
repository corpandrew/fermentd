# HTTPS for the dashboard (example: fermentd.example.com)

Replace `fermentd.example.com` with your domain and `100.64.0.1` with your Pi's Tailscale IP
(`tailscale ip -4`). `<user>` is the account fermentd runs as.

- DNS: an A record `fermentd.example.com -> 100.64.0.1`. It is a Tailscale address, so the name
  only resolves to something reachable on your tailnet.
- Caddy (apt) on the Pi binds the Tailscale IP on :443/:80 only and proxies to 127.0.0.1:8080;
  :80 redirects to https. Caddy does not get certs itself; it reads
  /etc/caddy/certs/fermentd.{crt,key} (dir `<user>:caddy`, mode 2750).
- Systemd drop-in /etc/systemd/system/caddy.service.d/tailscale.conf: After/Wants tailscaled,
  Restart=on-failure.
- Cert: Let's Encrypt via acme.sh (as `<user>`, ~/.acme.sh), DNS-01, ECC.
  `acme.sh --install-cert` copies to /etc/caddy/certs and runs `sudo systemctl reload caddy`
  (allowed by a one-line /etc/sudoers.d/caddy-reload rule).
- Renewal: with a DNS API (for example `--dns dns_vercel` with `VERCEL_TOKEN` exported once),
  acme.sh renews automatically from its cron job. A cert issued in manual DNS mode cannot.
- Login: set a dashboard password (`fermentd-ctl --config config/fermentd.yaml set-password`).
  If you open the dashboard through a different URL than the one in `web.url`, add it to
  `web.allowed_origins`.
