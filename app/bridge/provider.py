"""Provider capability bridge."""
import logging

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)

class ProviderBridge(QObject):
    error = Signal(str)

    def __init__(self, facade, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.facade.error.connect(self.error)

    @Slot(result=str)
    def get_providers(self) -> str:
        return self.facade.get_providers()

    @Slot(str, str, result=str)
    def validate_provider_key(self, provider_key: str, api_key: str) -> str:
        return self.facade.validate_provider_key(provider_key, api_key)

    @Slot(str, str)
    def save_provider_key(self, provider_key: str, api_key: str):
        self.facade.save_provider_key(provider_key, api_key)
