"""Gayatri AI — Application entry point."""

from __future__ import annotations

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

from core.config import WINDOW_HEIGHT, WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH, WINDOW_WIDTH
from core.logging_setup import setup_logging

import os
logger = setup_logging(os.environ.get("GAYATRI_LOG_LEVEL", "DEBUG"))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gayatri AI")
    app.setOrganizationName("Gayatri Education")

    from app.windows.main_window import MainWindow
    window = MainWindow()
    window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    window.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

    # Center on primary screen (frameless windows don't auto-center)
    screen = app.primaryScreen().availableGeometry()
    x = (screen.width() - WINDOW_WIDTH) // 2 + screen.x()
    y = (screen.height() - WINDOW_HEIGHT) // 2 + screen.y()
    window.move(x, y)

    window.show()
    window.raise_()
    window.activateWindow()

    logger.info("Gayatri AI started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
