from __future__ import annotations
from app.models.account import EmailAccount
from app.email.imap_client import ImapMailClient
from app.providers.microsoft_graph import MicrosoftGraphClient


def make_client(account: EmailAccount, device_login_callback=None, force_device: bool = False, cancel_event=None):
    # Outlook/Hotmail/Live should use OAuth + Microsoft Graph. Microsoft
    # disabled normal Basic Auth for Exchange Online/Outlook IMAP in most
    # scenarios, so falling back to client.login(email, password) is unreliable.
    if account.provider == "outlook":
        return MicrosoftGraphClient(account, device_login_callback=device_login_callback, force_device=force_device, cancel_event=cancel_event)
    return ImapMailClient(account)
