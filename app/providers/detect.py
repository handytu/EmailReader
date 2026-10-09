from __future__ import annotations

PROVIDERS = {
    "gmail.com": ("gmail", "imap.gmail.com", 993),
    "googlemail.com": ("gmail", "imap.gmail.com", 993),
    "outlook.com": ("outlook", "outlook.office365.com", 993),
    "hotmail.com": ("outlook", "outlook.office365.com", 993),
    "live.com": ("outlook", "outlook.office365.com", 993),
    "msn.com": ("outlook", "outlook.office365.com", 993),
    "yahoo.com": ("yahoo", "imap.mail.yahoo.com", 993),
    "ymail.com": ("yahoo", "imap.mail.yahoo.com", 993),
}

def detect_provider(email: str) -> tuple[str, str, int]:
    domain = email.rsplit("@", 1)[-1].lower().strip() if "@" in email else ""
    return PROVIDERS.get(domain, ("custom", "", 993))
