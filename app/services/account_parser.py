from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from app.models.account import EmailAccount
from app.providers.detect import detect_provider

@dataclass(slots=True)
class ImportReport:
    accounts: list[EmailAccount]
    invalid: list[tuple[int, str, str]]
    duplicates: int
    total_nonempty: int


def parse_accounts_file(path: str | Path) -> ImportReport:
    path = Path(path)
    accounts: list[EmailAccount] = []
    invalid: list[tuple[int, str, str]] = []
    seen: set[str] = set()
    duplicates = 0
    total_nonempty = 0

    for lineno, raw in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        total_nonempty += 1
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2 or "@" not in parts[0]:
            invalid.append((lineno, raw, "Expected email|password"))
            continue
        email, password = parts[0], parts[1]
        key = email.lower()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        provider, host, port = detect_provider(email)
        account = EmailAccount(email=email, password=password, provider=provider, imap_host=host, imap_port=port)

        # Extended formats supported now:
        # email|password|imap_host|imap_port
        # email|password|refresh_token|client_id
        # email|password|proxy
        if len(parts) >= 4 and parts[2] and parts[3].isdigit():
            account.imap_host = parts[2]
            account.imap_port = int(parts[3])
            if provider == "custom":
                account.provider = "custom"
        elif len(parts) >= 4 and parts[2] and parts[3]:
            account.refresh_token = parts[2]
            account.client_id = parts[3]
            if len(parts) >= 5 and parts[4]:
                account.proxy = parts[4]
        elif len(parts) >= 3 and parts[2]:
            third = parts[2]
            if "://" in third or third.count(":") >= 1:
                account.proxy = third
            else:
                account.refresh_token = third
        accounts.append(account)
    return ImportReport(accounts, invalid, duplicates, total_nonempty)
