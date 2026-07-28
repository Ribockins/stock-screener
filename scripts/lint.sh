#!/usr/bin/env bash
# Lint GEM platform in Cloud (Option C)
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
pip install -q ruff

echo "=== Syntax (compileall) ==="
python -m compileall -q src scripts gem_app.py rsiconfig.py
echo "OK"

echo ""
echo "=== Ruff check ==="
ruff check src scripts gem_app.py rsiconfig.py "$@"

echo ""
echo "=== Ruff format (check only) ==="
ruff format --check src scripts gem_app.py rsiconfig.py
