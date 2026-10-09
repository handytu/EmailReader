from __future__ import annotations
import imaplib
import smtplib
import socket
import ssl
from email.message import EmailMessage

from app.models.account import EmailAccount
from app.email.message_parser import parse_message


class EmailClientError(RuntimeError): pass
class AuthenticationError(EmailClientError): pass
class ConnectionTimeout(EmailClientError): pass
class SSLConnectionError(EmailClientError): pass
class NetworkError(EmailClientError): pass


SMTP_PROVIDERS = {
    "gmail": ("smtp.gmail.com", 465),
    "yahoo": ("smtp.mail.yahoo.com", 465),
}


class ImapMailClient:
    def __init__(self, account: EmailAccount, timeout: int = 20):
        self.account = account
        self.timeout = timeout
        self.client: imaplib.IMAP4 | imaplib.IMAP4_SSL | None = None

    def connect(self):
        if not self.account.imap_host:
            raise NetworkError("IMAP host is not configured")
        try:
            if self.account.use_ssl:
                self.client = imaplib.IMAP4_SSL(self.account.imap_host, self.account.imap_port, timeout=self.timeout)
            else:
                self.client = imaplib.IMAP4(self.account.imap_host, self.account.imap_port, timeout=self.timeout)
            self.client.login(self.account.email, self.account.password)
        except imaplib.IMAP4.error as e:
            raise AuthenticationError(str(e)) from e
        except (socket.timeout, TimeoutError) as e:
            raise ConnectionTimeout("Connection timed out") from e
        except ssl.SSLError as e:
            raise SSLConnectionError(str(e)) from e
        except OSError as e:
            raise NetworkError(str(e)) from e
        return self

    def close(self):
        if self.client:
            try: self.client.logout()
            except Exception: pass
            self.client = None

    def _select_rw(self):
        if not self.client:
            self.connect()
        assert self.client
        status, _ = self.client.select("INBOX", readonly=False)
        if status != "OK":
            raise EmailClientError("Cannot open Inbox")

    def fetch_inbox(self, limit: int = 50):
        if not self.client:
            self.connect()
        assert self.client
        status, _ = self.client.select("INBOX", readonly=True)
        if status != "OK":
            raise EmailClientError("Cannot open Inbox")
        status, data = self.client.uid("search", None, "ALL")
        if status != "OK":
            return []
        ids = data[0].split()[-limit:][::-1]
        result = []
        for uid_b in ids:
            uid = uid_b.decode()
            status, rows = self.client.uid("fetch", uid, "(BODY.PEEK[] FLAGS)")
            if status != "OK" or not rows:
                continue
            raw = b""
            flags: set[str] = set()
            for row in rows:
                if isinstance(row, tuple):
                    meta, body = row
                    raw = body or raw
                    meta_s = meta.decode(errors="ignore") if isinstance(meta, bytes) else str(meta)
                    for known in ("\\Seen", "\\Flagged"):
                        if known in meta_s: flags.add(known)
            if raw:
                result.append(parse_message(uid, raw, flags))
        return result

    def set_starred(self, uid: str, value: bool):
        self._select_rw()
        assert self.client
        op = "+FLAGS.SILENT" if value else "-FLAGS.SILENT"
        status, _ = self.client.uid("store", str(uid), op, "(\\Flagged)")
        if status != "OK":
            raise EmailClientError("Could not update star")
        return value

    def set_read(self, uid: str, value: bool):
        self._select_rw()
        assert self.client
        op = "+FLAGS.SILENT" if value else "-FLAGS.SILENT"
        status, _ = self.client.uid("store", str(uid), op, "(\\Seen)")
        if status != "OK":
            raise EmailClientError("Could not update read state")
        return value

    def delete_message(self, uid: str):
        self._select_rw()
        assert self.client
        status, _ = self.client.uid("store", str(uid), "+FLAGS.SILENT", "(\\Deleted)")
        if status != "OK":
            raise EmailClientError("Could not delete message")
        self.client.expunge()
        return True

    def send_message(self, *, to: list[str], cc: list[str], subject: str, body: str):
        if not to and not cc:
            raise EmailClientError("At least one recipient is required")
        provider = self.account.provider.lower()
        if provider in SMTP_PROVIDERS:
            host, port = SMTP_PROVIDERS[provider]
        elif self.account.imap_host:
            # Sensible custom-provider fallback; users with a different SMTP host
            # can still use Outlook Graph or provider-specific app passwords.
            host = self.account.imap_host.replace("imap.", "smtp.", 1)
            port = 465
        else:
            raise EmailClientError("SMTP server is not configured for this account")

        msg = EmailMessage()
        msg["From"] = self.account.email
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        msg.set_content(body or "")
        recipients = list(dict.fromkeys([*to, *cc]))
        try:
            with smtplib.SMTP_SSL(host, port, timeout=self.timeout) as smtp:
                smtp.login(self.account.email, self.account.password)
                smtp.send_message(msg, to_addrs=recipients)
        except smtplib.SMTPAuthenticationError as e:
            raise AuthenticationError("SMTP authentication failed; provider may require an app password") from e
        except (socket.timeout, TimeoutError) as e:
            raise ConnectionTimeout("SMTP connection timed out") from e
        except ssl.SSLError as e:
            raise SSLConnectionError(str(e)) from e
        except OSError as e:
            raise NetworkError(str(e)) from e
        return True
