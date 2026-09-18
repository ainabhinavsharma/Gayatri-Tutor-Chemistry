"""Model capability bridge."""
import logging

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)

class ModelBridge(QObject):
    token = Signal(int, str)
    done = Signal()
    error = Signal(str)

    def __init__(self, facade, parent=None):
        super().__init__(parent)
        self.facade = facade
        self.facade.token.connect(self.token)
        self.facade.done.connect(self.done)
        self.facade.error.connect(self.error)

    @Slot(result=str)
    def get_local_model_status(self) -> str:
        return self.facade.get_local_model_status()

    @Slot(result=str)
    def get_model_catalog(self) -> str:
        return self.facade.get_model_catalog()

    @Slot()
    def download_model(self):
        self.facade.download_model()

    @Slot()
    def cancel_model_download(self):
        self.facade.cancel_model_download()

    @Slot(result=str)
    def install_model(self) -> str:
        return self.facade.install_model()
