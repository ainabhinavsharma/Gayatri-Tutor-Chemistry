"""Gayatri AI — Main window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow

from app.bridge import Bridge
from core.config import BASE_DIR


class SecureWebPage(QWebEnginePage):
    """Enforces navigation hardening by only accepting local trusted UI assets."""
    def acceptNavigationRequest(self, url, _type, isMainFrame):
        scheme = url.scheme()
        if scheme in ("http", "https"):
            print(f"Blocked navigation to {url.toString()}")
            return False
        # Allow local files or qrc
        if scheme in ("file", "qrc", "data"):
            return True
        return False

class MainWindow(QMainWindow):
    """Frameless window with QWebEngineView + QWebChannel bridge."""

    def __init__(self, splash=None):
        super().__init__()
        import time
        self._start_time = time.time()
        self._splash = splash
        self._window_revealed = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowTitle("Gayatri AI")

        import sys

        from PySide6.QtGui import QIcon
        meipass = getattr(sys, "_MEIPASS", None)
        icon_candidates = [
            BASE_DIR / "gai3.ico",
            BASE_DIR / "gai3.png",
            Path(meipass) / "gai3.ico" if meipass else None,
            Path(meipass) / "gai3.png" if meipass else None,
        ]
        icon_path = next((p for p in icon_candidates if p and p.exists()), None)
        if icon_path:
            self.setWindowIcon(QIcon(str(icon_path)))

        # WebEngine view
        self._web = QWebEngineView()
        self._page = SecureWebPage()
        self._page.setBackgroundColor(QColor("#0f0f23"))
        self._web.setPage(self._page)
        self.setCentralWidget(self._web)

        # WebChannel + Bridge
        self._channel = QWebChannel()
        self._bridge = Bridge()

        # Sub-bridges
        from app.bridge.chat import ChatBridge
        from app.bridge.model import ModelBridge
        from app.bridge.provider import ProviderBridge
        from app.bridge.settings import SettingsBridge
        from app.bridge.window import WindowBridge

        self._chat_bridge = ChatBridge(self._bridge)
        self._settings_bridge = SettingsBridge(self._bridge)
        self._provider_bridge = ProviderBridge(self._bridge)
        self._model_bridge = ModelBridge(self._bridge)
        self._window_bridge = WindowBridge(self._bridge)

        # Register them
        self._channel.registerObject("bridge", self._bridge) # Facade for backwards compat
        self._channel.registerObject("chat_bridge", self._chat_bridge)
        self._channel.registerObject("settings_bridge", self._settings_bridge)
        self._channel.registerObject("provider_bridge", self._provider_bridge)
        self._channel.registerObject("model_bridge", self._model_bridge)
        self._channel.registerObject("window_bridge", self._window_bridge)

        self._web.page().setWebChannel(self._channel)
        self._bridge.set_view(self._web)
        self._bridge.set_window(self)

        # Connect loadFinished to only reveal window when fully rendered
        self._web.loadFinished.connect(self._on_web_loaded)
        from PySide6.QtCore import QTimer
        # Safety fallback timer in case loadFinished is delayed
        QTimer.singleShot(6000, self._reveal_window)

        # Load UI
        ui_path = BASE_DIR / "app" / "ui" / "index.html"
        if not ui_path.exists() and meipass:
            cand = Path(meipass) / "app" / "ui" / "index.html"
            if cand.exists():
                ui_path = cand
        if ui_path.exists():
            self._web.load(QUrl.fromLocalFile(str(ui_path)))
        else:
            self._web.setHtml(_FALLBACK_HTML)

        # Drag handling for frameless window
        self._dragging = False
        self._drag_offset = None

    def _on_web_loaded(self, ok: bool):
        """Called when QWebEngineView finishes loading HTML and assets."""
        import time

        from PySide6.QtCore import QTimer

        # Ensure splash is displayed for a minimum of 2.4 seconds
        elapsed = time.time() - getattr(self, "_start_time", time.time())
        min_duration = 2.4
        remaining_sec = max(0.1, min_duration - elapsed)
        delay_ms = int(remaining_sec * 1000)

        if self._splash:
            QTimer.singleShot(
                max(0, delay_ms - 300),
                lambda: self._splash.update_status("Ready! Opening workspace...", 100) if self._splash else None
            )

        QTimer.singleShot(delay_ms, self._reveal_window)

    def _reveal_window(self):
        """Reveal main window and close splash screen."""
        if self._window_revealed:
            return
        self._window_revealed = True
        self.show()
        self.raise_()
        self.activateWindow()
        if self._splash:
            try:
                self._splash.close()
            except Exception:
                pass
            self._splash = None



    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_offset:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._drag_offset = None


_FALLBACK_HTML = """<!DOCTYPE html>
<html>
<head><title>Gayatri AI</title></head>
<body style="margin:0;background:#1a1a2e;color:#eee;font-family:system-ui;">
<div style="display:flex;height:100vh">
  <div style="width:60px;background:#16213e;display:flex;flex-direction:column;align-items:center;padding:10px 0;">
    <div style="width:32px;height:32px;background:#e94560;border-radius:8px;margin-bottom:10px;"></div>
  </div>
  <div style="flex:1;display:flex;flex-direction:column;">
    <div style="padding:12px 20px;border-bottom:1px solid #333;font-weight:600;">Gayatri AI</div>
    <div id="messages" style="flex:1;overflow-y:auto;padding:20px;"></div>
    <div style="padding:12px 20px;border-top:1px solid #333;display:flex;gap:8px;">
      <input id="input" type="text" placeholder="Type a message..."
             style="flex:1;padding:8px 12px;border-radius:8px;border:1px solid #333;background:#16213e;color:#eee;outline:none;">
      <button id="send" style="padding:8px 16px;border-radius:8px;border:none;background:#e94560;color:#fff;cursor:pointer;">Send</button>
    </div>
  </div>
</div>
<script src="qrc:/qtwebchannel/qwebchannel.js"></script>
<script>
  window._tokens = [];
  var channel = new QWebChannel(qt.webChannelTransport);
  var bridge = channel.objects.bridge;
  document.getElementById('send').onclick = function() {
    var input = document.getElementById('input');
    bridge.send_message(input.value);
    var el = document.getElementById('messages');
    var p = document.createElement('div');
    p.style.marginBottom = '12px';
    p.textContent = 'You: ' + input.value;
    el.appendChild(p);
    input.value = '';
  };
</script>
</body>
</html>"""
