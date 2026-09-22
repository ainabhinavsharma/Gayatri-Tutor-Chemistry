"""Chat capability bridge."""
import logging

from PySide6.QtCore import QObject, Signal, Slot

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
    def send_message(self, message: str, mode: str = "general_assistant"):
        self.facade.send_message(message, mode)

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
    def get_session_messages(self, session_id: str) -> str:
        return self.facade.get_session_messages(session_id)

    @Slot(str, result=str)
    def delete_session(self, session_id: str) -> str:
        return self.facade.delete_session(session_id)

    @Slot(result=str)
    def get_agents(self) -> str:
        return self.facade.get_agents()

    @Slot(result=str)
    def get_curriculum_progress(self) -> str:
        return self.facade.get_curriculum_progress()
