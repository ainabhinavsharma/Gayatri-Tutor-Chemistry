"""Window capability bridge."""
from PySide6.QtCore import QObject, Slot


class WindowBridge(QObject):
    def __init__(self, facade, parent=None):
        super().__init__(parent)
        self.facade = facade

    @Slot()
    def minimize_window(self):
        self.facade.minimize_window()

    @Slot()
    def maximize_window(self):
        self.facade.maximize_window()

    @Slot()
    def close_window(self):
        self.facade.close_window()
