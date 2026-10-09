"""Persist imported accounts with Windows user-bound credential protection."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
from dataclasses import asdict
from app.models.account import EmailAccount


class DataBlob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def protect_data(data: bytes, decrypt: bool = False) -> bytes:
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = DataBlob(len(data), buffer)
    result = DataBlob()
    name = "CryptUnprotectData" if decrypt else "CryptProtectData"
    function = getattr(crypt, name)
    function.argtypes = [ctypes.POINTER(DataBlob), ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                         wintypes.DWORD, ctypes.POINTER(DataBlob)]
    function.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel.LocalFree(result.data)


class AccountStore:
    def __init__(self, path: Path):
        self.path = path

    def save(self, accounts: dict[str, EmailAccount]):
        rows = []
        for account in accounts.values():
            row = asdict(account)
            for transient in ("state", "error", "unread"):
                row.pop(transient)
            rows.append(row)
        encrypted = protect_data(json.dumps(rows).encode("utf-8"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(encrypted)
        temporary.replace(self.path)

    def load(self) -> dict[str, EmailAccount]:
        if not self.path.exists():
            return {}
        rows = json.loads(protect_data(self.path.read_bytes(), decrypt=True))
        accounts = [EmailAccount(**row) for row in rows]
        return {account.email.lower(): account for account in accounts}
