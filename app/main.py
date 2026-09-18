"""Gayatri AI — Application entry point."""

from __future__ import annotations

import sys

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
    window.show()

    logger.info("Gayatri AI started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
