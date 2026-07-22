#!/usr/bin/env python3
"""
GEM Logic Platform — desktop entry point.

Install:  ./install.sh   (Linux/macOS)  or  install.bat  (Windows)
Run:      python gem_app.py
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("gem_platform.log"),
    ],
)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    try:
        from PyQt6.QtWidgets import QApplication
        from src.ui.gem_main_window import GemMainWindow
    except ImportError as e:
        print("Missing dependencies. Run the installer first:")
        print("  ./install.sh   or   install.bat")
        print(f"Error: {e}")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("GEM Logic Platform")
    window = GemMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
