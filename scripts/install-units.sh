#!/usr/bin/env bash
# Render the systemd units in deploy/ for this checkout and install them. Run on the Pi:
#   scripts/install-units.sh              (user = you, app dir = this checkout)
#   FERMENTD_USER=pi FERMENTD_DIR=/home/pi/fermentd scripts/install-units.sh
#   DRY_RUN=1 scripts/install-units.sh    (print the rendered units, change nothing)
set -euo pipefail
cd "$(dirname "$0")/.."
USER_NAME="${FERMENTD_USER:-$(id -un)}"
APP_DIR="${FERMENTD_DIR:-$(pwd)}"
UNITS=(deploy/systemd/fermentd-control.service deploy/systemd/fermentd-web.service
       deploy/systemd/fermentd-mcp.service deploy/backup/fermentd-backup.service
       deploy/backup/fermentd-backup.timer)
render() { sed -e "s|@USER@|$USER_NAME|g" -e "s|@APP_DIR@|$APP_DIR|g" "$1"; }
for unit in "${UNITS[@]}"; do
  if [ -n "${DRY_RUN:-}" ]; then
    echo "### $(basename "$unit")"; render "$unit"
  else
    render "$unit" | sudo tee "/etc/systemd/system/$(basename "$unit")" >/dev/null
  fi
done
[ -n "${DRY_RUN:-}" ] && exit 0
sudo systemctl daemon-reload
sudo systemctl enable fermentd-control fermentd-web fermentd-mcp fermentd-backup.timer
echo "installed units for $USER_NAME at $APP_DIR; restart with: .venv/bin/fermentd-ctl --config config/fermentd.yaml planned-restart"
