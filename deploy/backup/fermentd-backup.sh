#!/usr/bin/env bash
# Nightly online backup of the fermentd SQLite database (safe while services run).
# Writes ~/fermentd-backups/fermentd-YYYYMMDD.db.gz, checks integrity, keeps the newest 14.
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DB="${FERMENTD_DB:-$APP_DIR/data/fermentd.db}"
DEST="${FERMENTD_BACKUP_DIR:-$HOME/fermentd-backups}"
KEEP="${FERMENTD_BACKUP_KEEP:-14}"
mkdir -p "$DEST"
stamp="$(date +%Y%m%d)"
tmp="$DEST/.fermentd-$stamp.db.tmp"
rm -f "$tmp"
sqlite3 "$DB" ".timeout 30000" ".backup '$tmp'"
check="$(sqlite3 "$tmp" 'PRAGMA integrity_check;')"
if [ "$check" != "ok" ]; then
  echo "fermentd backup FAILED integrity check: $check" >&2
  rm -f "$tmp"; exit 1
fi
gzip -9 -c "$tmp" > "$DEST/fermentd-$stamp.db.gz.part"
mv "$DEST/fermentd-$stamp.db.gz.part" "$DEST/fermentd-$stamp.db.gz"
rm -f "$tmp"
ls -1t "$DEST"/fermentd-*.db.gz | tail -n +"$((KEEP + 1))" | xargs -r rm -f
echo "fermentd backup ok: $DEST/fermentd-$stamp.db.gz ($(stat -c %s "$DEST/fermentd-$stamp.db.gz") bytes)"
