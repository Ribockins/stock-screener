#!/usr/bin/env bash
# Background GEM monitor for Cloud VM (no local PC required)
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate

INTERVAL="${GEM_REFRESH_MINUTES:-5}"
INTERVAL_SEC=$((INTERVAL * 60))

echo "Cloud GEM monitor — every ${INTERVAL} min — Ctrl+C to stop"
while true; do
  echo "=== $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
  python scripts/cloud_gem_report.py || true
  sleep "$INTERVAL_SEC"
done
