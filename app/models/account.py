from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class AccountState(str, Enum):
    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    AUTH_FAILED = "AUTH_FAILED"
    TIMEOUT = "TIMEOUT"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"

@dataclass(slots=True)
class EmailAccount:
    email: str
    password: str = field(repr=False, default="")
    provider: str = "custom"
    imap_host: str = ""
    imap_port: int = 993
    use_ssl: bool = True
    refresh_token: str = field(repr=False, default="")
    client_id: str = ""
    proxy: str = field(repr=False, default="")
    state: AccountState = AccountState.IDLE
    error: str = ""
    unread: int = 0

    @property
    def display_name(self) -> str:
        return self.email

    def public_dict(self) -> dict:
        return {
            "email": self.email,
            "provider": self.provider,
            "imap_host": self.imap_host,
            "imap_port": self.imap_port,
            "use_ssl": self.use_ssl,
            "state": self.state.value,
            "error": self.error,
            "unread": self.unread,
        }
