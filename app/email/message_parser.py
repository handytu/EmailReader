from __future__ import annotations
import email
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime, parseaddr, getaddresses
from html import unescape
import re
from app.models.message import MailMessage

TAG_RE = re.compile(r"<[^>]+>")

def decode_mime(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value

def _payload_text(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")

def parse_message(uid: str, raw: bytes, flags: set[str] | None = None) -> MailMessage:
    msg = email.message_from_bytes(raw)
    sender_name, sender_addr = parseaddr(decode_mime(msg.get("From")))
    reply_to_addr = parseaddr(decode_mime(msg.get("Reply-To")))[1]
    to_addrs = [addr for _, addr in getaddresses(msg.get_all("To", [])) if addr]
    cc_addrs = [addr for _, addr in getaddresses(msg.get_all("Cc", [])) if addr]
    subject = decode_mime(msg.get("Subject")) or "(No subject)"
    try:
        dt = parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None
    except Exception:
        dt = None
    html_body, text_body = "", ""
    attachments = []
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        ctype = part.get_content_type()
        disp = (part.get("Content-Disposition") or "").lower()
        filename = decode_mime(part.get_filename())
        if filename or "attachment" in disp:
            data = part.get_payload(decode=True) or b""
            attachments.append({"name": filename or "attachment", "size": len(data)})
            continue
        if ctype == "text/plain" and not text_body:
            text_body = _payload_text(part)
        elif ctype == "text/html" and not html_body:
            html_body = _payload_text(part)
    preview_src = text_body or unescape(TAG_RE.sub(" ", html_body))
    preview = re.sub(r"\s+", " ", preview_src).strip()[:240]
    flags = flags or set()
    return MailMessage(
        uid=str(uid), sender_name=sender_name, sender_addr=sender_addr,
        subject=subject, preview=preview, date=dt,
        is_read="\\Seen" in flags, is_starred="\\Flagged" in flags,
        body_html=html_body, body_text=text_body,
        message_id=msg.get("Message-ID", ""), to_addrs=to_addrs, cc_addrs=cc_addrs,
        reply_to_addr=reply_to_addr, attachments=attachments,
    )
