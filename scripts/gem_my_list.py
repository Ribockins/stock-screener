#!/usr/bin/env python3
"""Run GEM My List — colour-coded trade board (see src/gem_colours.py)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Reuse full MTF scan + report; prints GEM My List section first
from scripts.cloud_gem_report import main

if __name__ == "__main__":
    main()
