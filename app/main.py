"""Gayatri AI — Application entry point."""

from __future__ import annotations

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def check_dependencies() -> tuple[bool, list[str]]:
    """Verify essential runtime dependencies are available before launching Qt."""
    missing: list[str] = []
    
    # Check PySide6
    try:
        import PySide6.QtWidgets  # noqa: F401
    except ImportError as e:
        missing.append(f"PySide6 ({e})")
        
    # Check sqlite3
    try:
        import sqlite3  # noqa: F401
    except ImportError as e:
        missing.append(f"sqlite3 ({e})")
        
    # Check core configuration
    try:
        import core.config  # noqa: F401
    except ImportError as e:
        missing.append(f"core.config ({e})")
        
    return len(missing) == 0, missing


def main():
    # CLI Flags
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Gayatri AI Tutor")
        print("Usage: python -m app.main [options]")
        print("Options:")
        print("  --check-startup  Verify dependencies and configuration headlessly")
        print("  --version, -v    Display application version")
        print("  --help, -h       Display this help message")
        sys.exit(0)

    if "--version" in sys.argv or "-v" in sys.argv:
        try:
            from core.config import APP_VERSION
            print(f"Gayatri AI v{APP_VERSION}")
        except Exception:
            version_file = PROJECT_ROOT / "VERSION"
            print(f"Gayatri AI v{version_file.read_text().strip() if version_file.exists() else '3.0.0'}")
        sys.exit(0)

    ok, missing = check_dependencies()
    if not ok:
        sys.stderr.write("[ERROR] Cannot start Gayatri AI. Required dependencies are missing:\n")
        for m in missing:
            sys.stderr.write(f"  - {m}\n")
        sys.stderr.write("Please run: pip install -r requirements.txt\n")
        sys.exit(1)

    if "--check-startup" in sys.argv:
        print("[OK] Startup verification passed. All essential dependencies and configurations are healthy.")
        sys.exit(0)

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("gayatri.chemistry.tutor.v3")
        except Exception:
            pass

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from core.config import WINDOW_HEIGHT, WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH, WINDOW_WIDTH
    from core.logging_setup import setup_logging

    logger = setup_logging(os.environ.get("GAYATRI_LOG_LEVEL", "DEBUG"))

    app = QApplication(sys.argv)
    app.setApplicationName("Gayatri AI")
    app.setOrganizationName("Gayatri Education")

    icon_path = PROJECT_ROOT / "gai3.ico" if (PROJECT_ROOT / "gai3.ico").exists() else PROJECT_ROOT / "gai3.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    from app.windows.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    splash.update_status("Starting local environment...", 20)
    app.processEvents()

    # Single-instance enforcement via QLocalServer
    server_name = "gayatri_ai_single_instance_lock"
    probe_socket = QLocalSocket()
    probe_socket.connectToServer(server_name)
    if probe_socket.waitForConnected(500):
        # Notify existing instance to bring window to front and exit
        probe_socket.write(b"ACTIVATE\n")
        probe_socket.flush()
        probe_socket.waitForBytesWritten(500)
        probe_socket.close()
        splash.close()
        logger.info("Another instance of Gayatri AI is already running. Focused existing instance.")
        sys.exit(0)

    splash.update_status("Loading Socratic engine & NCERT knowledge...", 50)
    app.processEvents()

    # Primary instance: create server
    server = QLocalServer(app)
    server.removeServer(server_name)  # Clean up any stale pipe/socket from previous unclean exit
    if not server.listen(server_name):
        logger.warning(f"Could not bind single instance server: {server.errorString()}")

    splash.update_status("Initializing workspace...", 75)
    app.processEvents()

    from app.windows.main_window import MainWindow
    window = MainWindow(splash=splash)
    window.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    window.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

    def _on_new_connection():
        sock = server.nextPendingConnection()
        if sock:
            sock.waitForReadyRead(500)
            window.showNormal()
            window.raise_()
            window.activateWindow()
            sock.close()

    server.newConnection.connect(_on_new_connection)

    # Center on primary screen (frameless windows don't auto-center)
    screen = app.primaryScreen().availableGeometry()
    x = (screen.width() - WINDOW_WIDTH) // 2 + screen.x()
    y = (screen.height() - WINDOW_HEIGHT) // 2 + screen.y()
    window.move(x, y)

    # Window is revealed automatically by MainWindow when WebEngine loadFinished fires
    logger.info("Gayatri AI started")
    sys.exit(app.exec())



if __name__ == "__main__":
    main()

