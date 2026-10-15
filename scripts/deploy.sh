#!/usr/bin/env bash
# Deploy this working tree to the Pi and restart without a "service interrupted" alert.
#   scripts/deploy.sh            (host defaults to "fermentd", repo to ~/fermentd)
set -euo pipefail
# Stale stdio MCP sessions keep serving the old code after a restart (the client reuses them).
# The [p] keeps pkill from matching the shell that runs it. The HTTP service runs as
# `fermentd-mcp --http`, so it does not match.
PI_STDIO_PATTERN='[p]ython -m fermentd.mcp --db'
LOCAL_STDIO_PATTERN='^ssh -T fermentd .*-m fermentd[.]mcp'
HOST="${1:-fermentd}"
REMOTE_DIR="${REMOTE_DIR:-fermentd}"
cd "$(dirname "$0")/.."
rsync -az \
  --exclude .git --exclude .venv --exclude data \
  --exclude config/fermentd.yaml --exclude config/secrets.yaml --exclude config/fermentd.env \
  --exclude '*.pem' --exclude '*.key' --exclude .env --exclude photos \
  --exclude devices.json --exclude tuya-raw.json --exclude snapshot.json \
  --exclude '*.egg-info' --exclude __pycache__ --exclude .pytest_cache --exclude .ruff_cache \
  ./ "$HOST:$REMOTE_DIR/"
ssh "$HOST" "cd $REMOTE_DIR && .venv/bin/pip install -q -e . && \
  .venv/bin/fermentd-ctl --config config/fermentd.yaml planned-restart && \
  sleep 8 && systemctl is-active fermentd-control fermentd-web fermentd-mcp"
# End stdio MCP sessions on both ends; the MCP client starts a fresh one on its next call.
ssh "$HOST" "pkill -f '$PI_STDIO_PATTERN' && echo 'ended stale stdio MCP sessions on the Pi' || echo 'no stdio MCP sessions on the Pi'"
if pkill -f "$LOCAL_STDIO_PATTERN"; then
  echo "ended stale local ssh MCP sessions"
else
  echo "no local ssh MCP sessions"
fi
