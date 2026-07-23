#!/usr/bin/env bash
# GEM Logic Platform — one-shot installer (Linux / macOS)
set -euo pipefail
cd "$(dirname "$0")"

echo "==> GEM Logic Platform installer"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install Python 3.10+ and re-run."
  exit 1
fi

PY=python3
if ! $PY -c "import venv" 2>/dev/null; then
  echo "Note: python3-venv missing; trying virtualenv via pip --user"
  $PY -m pip install --user virtualenv
  export PATH="$HOME/.local/bin:$PATH"
  virtualenv .venv
else
  $PY -m venv .venv 2>/dev/null || virtualenv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel

echo "==> Installing Python packages"
pip install -r requirements-platform.txt

echo "==> Installing tvdatafeed from GitHub"
pip install --no-cache-dir "git+https://github.com/rongardF/tvdatafeed.git"

echo "==> tvdatafeed import shim (Linux case sensitivity)"
SHIM="$(python -c 'import site; print(site.getsitepackages()[0])')/tvdatafeed"
mkdir -p "$SHIM"
echo 'from tvDatafeed import *' > "$SHIM/__init__.py"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

if [ ! -f config/watchlist.json ]; then
  mkdir -p config
  echo "Using default config/watchlist.json"
fi

chmod +x gem_app.py scripts/run_gem_monitor.py 2>/dev/null || true

echo ""
echo "Installation complete."
echo "  Desktop app:  source .venv/bin/activate && python gem_app.py"
echo "  CLI monitor:  source .venv/bin/activate && python scripts/run_gem_monitor.py --once"
echo "  Edit symbols: config/watchlist.json"
echo ""
