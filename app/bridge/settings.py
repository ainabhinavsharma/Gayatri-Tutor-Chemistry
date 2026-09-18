"""Settings capability bridge."""
import logging

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)

class SettingsBridge(QObject):
    error = Signal(str)

    def __init__(self, facade, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.facade.error.connect(self.error)

    @Slot(str, str)
    def set_setting(self, key: str, value: str):
        from core.settings import _SETTINGS_SCHEMA
        if key not in _SETTINGS_SCHEMA:
            self.error.emit(f"Unknown setting key: '{key}'")
            return
        self.facade.set_setting(key, value)

    @Slot(str, result=str)
    def get_setting(self, key: str) -> str:
        return self.facade.get_setting(key)
