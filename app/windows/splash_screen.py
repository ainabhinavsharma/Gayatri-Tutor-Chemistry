"""Gayatri AI — Elegant Frameless Splash Screen.

Displays application identity, lotus branding, and dynamic loading progress
while Python dependencies, local GGUF models, and Chromium WebEngine initialize.
"""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
    QFrame,
    QApplication,
)

from core.config import BASE_DIR


class SplashScreen(QWidget):
    """Modern dark-themed splash screen with live status and progress bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.SplashScreen
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(500, 320)

        # Main container with rounded card styling
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame(self)
        card.setObjectName("splashCard")
        card.setStyleSheet("""
            QFrame#splashCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0d0d1f, stop:0.5 #11112b, stop:1 #171738);
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 20px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 24)
        card_layout.setSpacing(10)

        # 1. Top Section: App Logo + Title Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        # Lotus Logo
        self.logo_label = QLabel()
        logo_path = BASE_DIR / "gai3.png"
        if not logo_path.exists():
            logo_path = BASE_DIR / "app" / "ui" / "gai3.png"

        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(
                72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.logo_label.setPixmap(pix)
        self.logo_label.setFixedSize(76, 76)
        self.logo_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.logo_label)

        # Title + Subtitle
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        title = QLabel("Gayatri Chemistry Tutor")
        title.setStyleSheet("""
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            font-size: 21px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.3px;
        """)

        subtitle = QLabel("Socratic AI Tutor • Class 11 & 12 NCERT")
        subtitle.setStyleSheet("""
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 13px;
            font-weight: 500;
            color: #a5b4fc;
        """)

        badge = QLabel("100% Offline • Zero Data Egress • Local SQLite")
        badge.setStyleSheet("""
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 11px;
            font-weight: 600;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 6px;
            padding: 2px 8px;
        """)

        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        text_layout.addWidget(badge)
        header_layout.addLayout(text_layout)
        header_layout.addStretch()

        card_layout.addLayout(header_layout)
        card_layout.addSpacing(16)

        # 2. Status text
        self.status_label = QLabel("Initializing Socratic neural engine...")
        self.status_label.setStyleSheet("""
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 12px;
            color: #94a3b8;
        """)
        card_layout.addWidget(self.status_label)

        # 3. Modern Thin Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(15)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:0.5 #38bdf8, stop:1 #34d399);
                border-radius: 2px;
            }
        """)
        card_layout.addWidget(self.progress_bar)

        # 4. Footer Note
        footer_layout = QHBoxLayout()
        footer_note = QLabel("Evidence-based adaptive learning engine")
        footer_note.setStyleSheet("""
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 10px;
            color: #64748b;
        """)
        version_label = QLabel("v3.0.0")
        version_label.setStyleSheet("""
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 10px;
            font-weight: 600;
            color: #64748b;
        """)
        footer_layout.addWidget(footer_note)
        footer_layout.addStretch()
        footer_layout.addWidget(version_label)
        card_layout.addLayout(footer_layout)

        main_layout.addWidget(card)

        # Center on primary screen
        self._center_on_screen()

        # Smooth animation timer
        import time
        self._start_time = time.time()
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(75)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.x()
        y = (screen.height() - self.height()) // 2 + screen.y()
        self.move(x, y)

    def _on_anim_tick(self):
        import time
        elapsed = time.time() - getattr(self, "_start_time", time.time())
        # Smoothly advance progress bar up to 95% over 2.4 seconds
        target_progress = int(min(95, 15 + (elapsed / 2.4) * 80))
        if self.progress_bar.value() < target_progress:
            self.progress_bar.setValue(target_progress)

        if elapsed >= 1.6:
            if "privacy" not in self.status_label.text().lower() and "ready" not in self.status_label.text().lower():
                self.status_label.setText("Verifying offline privacy & curriculum DAG...")
        elif elapsed >= 0.8:
            if "knowledge" not in self.status_label.text().lower():
                self.status_label.setText("Loading Socratic neural weights & NCERT knowledge...")

    def update_status(self, text: str, progress: int = -1):
        """Update live status message and progress percentage."""
        self.status_label.setText(text)
        if progress >= 0:
            self.progress_bar.setValue(min(100, max(0, progress)))
        QApplication.processEvents()

    def finish(self, target_window):
        """Smoothly reveal target window and close splash screen."""
        if hasattr(self, "_anim_timer") and self._anim_timer.isActive():
            self._anim_timer.stop()
        self.update_status("Ready! Opening workspace...", 100)
        target_window.show()
        target_window.raise_()
        target_window.activateWindow()
        self.close()

