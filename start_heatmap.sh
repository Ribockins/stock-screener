#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "First-time setup..."
  ./install.sh
fi
source .venv/bin/activate
echo "Opening GEM Heatmap at http://localhost:8501"
streamlit run heatmap_app.py --server.headless true
