"""
Stock Signal Monitor - Desktop Application Entry Point

This script initializes and runs the PyQt6 desktop application for the RSI & Divergence Stock Screener.
It serves as the main entry point for the desktop UI.

Usage:
    python desktop_app.py
"""

import sys
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_screener.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for desktop application"""
    try:
        # Add project root to path for imports
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        # Import after path is set
        from PyQt6.QtWidgets import QApplication
        from src.ui.main_window import MainWindow
        
        logger.info("=" * 60)
        logger.info("Starting Stock Signal Monitor Application")
        logger.info("=" * 60)
        
        # Create Qt application
        app = QApplication(sys.argv)
        
        # Set application metadata
        app.setApplicationName("Stock Signal Monitor")
        app.setApplicationVersion("1.0.0")
        
        # Create and show main window
        main_window = MainWindow()
        main_window.show()
        
        logger.info("Main window displayed successfully")
        
        # Run application event loop
        sys.exit(app.exec())
        
    except ImportError as e:
        logger.error(f"Import Error: {e}")
        logger.error("Please install dependencies: pip install -r requirements_desktop.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
