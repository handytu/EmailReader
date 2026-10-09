from __future__ import annotations
from PySide6.QtCore import QObject, Signal, Slot
from threading import Event
from app.models.account import EmailAccount, AccountState
from app.services.mail_service import make_client
from app.email.imap_client import AuthenticationError, ConnectionTimeout, SSLConnectionError, NetworkError

class FetchWorker(QObject):
    status = Signal(str, str, str)   # email, state, detail
    fetched = Signal(str, object)    # email, messages
    finished = Signal()
    device_login = Signal(str, str, str, str)  # email, verification_uri, user_code, message

    def __init__(self, account: EmailAccount, limit: int = 50, force_device: bool = False):
        super().__init__()
        self.account = account
        self.limit = limit
        self.force_device = force_device
        self.cancel_event = Event()

    def cancel(self):
        self.cancel_event.set()

    def _device_login_info(self, verification_uri: str, user_code: str, message: str):
        self.status.emit(self.account.email, AccountState.CONNECTING.value, "Waiting for Microsoft sign-in…")
        self.device_login.emit(self.account.email, verification_uri, user_code, message)

    @Slot()
    def run(self):
        client = None
        try:
            if self.cancel_event.is_set():
                return
            self.status.emit(self.account.email, AccountState.CONNECTING.value, "Connecting…")
            client = make_client(self.account, device_login_callback=self._device_login_info, force_device=self.force_device, cancel_event=self.cancel_event)
            client.connect()
            if self.cancel_event.is_set():
                return
            self.status.emit(self.account.email, AccountState.CONNECTED.value, "Connected")
            messages = client.fetch_inbox(self.limit)
            if self.cancel_event.is_set():
                return
            self.fetched.emit(self.account.email, messages)
        except AuthenticationError as e:
            self.status.emit(self.account.email, AccountState.AUTH_FAILED.value, str(e))
        except ConnectionTimeout as e:
            self.status.emit(self.account.email, AccountState.TIMEOUT.value, str(e))
        except (SSLConnectionError, NetworkError) as e:
            self.status.emit(self.account.email, AccountState.OFFLINE.value, str(e))
        except Exception as e:
            self.status.emit(self.account.email, AccountState.ERROR.value, str(e))
        finally:
            if client:
                try: client.close()
                except Exception: pass
            self.finished.emit()
