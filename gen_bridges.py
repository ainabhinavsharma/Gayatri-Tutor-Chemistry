import os

os.makedirs('app/bridge', exist_ok=True)

with open('app/bridge/chat.py', 'w', encoding='utf-8') as f:
    f.write('''"""Chat capability bridge."""
from PySide6.QtCore import QObject, Signal, Slot
import json
import logging
logger = logging.getLogger(__name__)

class ChatBridge(QObject):
    token = Signal(int, str)
    done = Signal()
    error = Signal(str)

    def __init__(self, facade, parent=None):
        super().__init__(parent)
        self.facade = facade
        # connect signals
        self.facade.token.connect(self.token)
        self.facade.done.connect(self.done)
        self.facade.error.connect(self.error)

    @Slot(str)
    @Slot(str, str)
    def send_message(self, message: str, agent_name: str = ""):
        self.facade.send_message(message, agent_name)

    @Slot()
    def new_chat(self):
        self.facade.new_chat()

    @Slot(result=str)
    def get_sessions(self) -> str:
        return self.facade.get_sessions()

    @Slot(str)
    def load_session_id(self, session_id: str):
        self.facade.load_session_id(session_id)

    @Slot(str, result=str)
    def delete_session(self, session_id: str) -> str:
        return self.facade.delete_session(session_id)

    @Slot(result=str)
    def get_agents(self) -> str:
        return self.facade.get_agents()

    @Slot(result=str)
    def get_curriculum_progress(self) -> str:
        return self.facade.get_curriculum_progress()
''')

with open('app/bridge/settings.py', 'w', encoding='utf-8') as f:
    f.write('''"""Settings capability bridge."""
from PySide6.QtCore import QObject, Signal, Slot
import json
import logging
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
''')

with open('app/bridge/provider.py', 'w', encoding='utf-8') as f:
    f.write('''"""Provider capability bridge."""
from PySide6.QtCore import QObject, Signal, Slot
import json
import logging
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
''')

with open('app/bridge/model.py', 'w', encoding='utf-8') as f:
    f.write('''"""Model capability bridge."""
from PySide6.QtCore import QObject, Signal, Slot
import json
import logging
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
''')

with open('app/bridge/window.py', 'w', encoding='utf-8') as f:
    f.write('''"""Window capability bridge."""
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
''')
