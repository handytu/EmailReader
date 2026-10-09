from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(slots=True)
class MailMessage:
    uid: str
    folder: str = "INBOX"
    sender_name: str = ""
    sender_addr: str = ""
    subject: str = "(No subject)"
    preview: str = ""
    date: datetime | None = None
    is_read: bool = False
    is_starred: bool = False
    body_html: str = ""
    body_text: str = ""
    message_id: str = ""
    to_addrs: list[str] = field(default_factory=list)
    cc_addrs: list[str] = field(default_factory=list)
    reply_to_addr: str = ""
    attachments: list[dict] = field(default_factory=list)
