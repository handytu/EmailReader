from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot
from threading import Event

from app.models.account import EmailAccount
from app.services.mail_service import make_client


class MailActionWorker(QObject):
    succeeded = Signal(str, object)   # action, payload
    failed = Signal(str, str)         # action, error
    finished = Signal()

    def __init__(self, account: EmailAccount, action: str, payload: dict):
        super().__init__()
        self.account = account
        self.action = action
        self.payload = payload
        self.cancel_event = Event()

    def cancel(self):
        self.cancel_event.set()

    @Slot()
    def run(self):
        client = None
        try:
            if self.cancel_event.is_set():
                return
            client = make_client(self.account, cancel_event=self.cancel_event)
            client.connect()
            if self.cancel_event.is_set():
                return
            if self.action == "star":
                result = client.set_starred(self.payload["uid"], bool(self.payload["value"]))
            elif self.action == "read":
                result = client.set_read(self.payload["uid"], bool(self.payload["value"]))
            elif self.action == "delete":
                result = client.delete_message(self.payload["uid"])
            elif self.action == "send":
                result = client.send_message(
                    to=self.payload.get("to", []),
                    cc=self.payload.get("cc", []),
                    subject=self.payload.get("subject", ""),
                    body=self.payload.get("body", ""),
                )
            else:
                raise RuntimeError(f"Unknown mail action: {self.action}")
            self.succeeded.emit(self.action, result)
        except Exception as exc:
            self.failed.emit(self.action, str(exc))
        finally:
            if client:
                try:
                    client.close()
                except Exception:
                    pass
            self.finished.emit()
