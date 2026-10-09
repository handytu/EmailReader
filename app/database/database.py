from __future__ import annotations
import sqlite3
import json
from dataclasses import asdict
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from app.models.message import MailMessage

class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._init()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _init(self):
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS messages(
                account TEXT NOT NULL, folder TEXT NOT NULL, uid TEXT NOT NULL,
                sender_name TEXT, sender_addr TEXT, subject TEXT, date TEXT,
                preview TEXT, is_read INTEGER NOT NULL DEFAULT 0,
                is_starred INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(account, folder, uid))""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(messages)")}
            if "payload" not in columns:
                db.execute("ALTER TABLE messages ADD COLUMN payload TEXT")

    def cache_messages(self, account: str, messages: list[MailMessage]):
        with self.connect() as db:
            # Each successful inbox fetch is a snapshot, including an empty inbox.
            db.execute("DELETE FROM messages WHERE account=?", (account,))
            db.executemany("""INSERT OR REPLACE INTO messages
                (account,folder,uid,sender_name,sender_addr,subject,date,preview,is_read,is_starred,payload)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""", [(
                    account, m.folder, m.uid, m.sender_name, m.sender_addr, m.subject,
                    m.date.isoformat() if m.date else "", m.preview, int(m.is_read), int(m.is_starred),
                    json.dumps({**asdict(m), "date": m.date.isoformat() if m.date else None})
                ) for m in messages])

    def load_messages(self, account: str) -> list[MailMessage]:
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM messages WHERE account=? ORDER BY rowid", (account,)).fetchall()
        messages = []
        for row in rows:
            if row["payload"]:
                values = json.loads(row["payload"])
            else:
                values = {key: row[key] for key in ("uid", "folder", "sender_name", "sender_addr", "subject", "date", "preview", "is_read", "is_starred")}
            values["date"] = datetime.fromisoformat(values["date"]) if values.get("date") else None
            values["is_read"] = bool(values["is_read"])
            values["is_starred"] = bool(values["is_starred"])
            messages.append(MailMessage(**values))
        return messages

    def delete_message(self, account: str, folder: str, uid: str):
        with self.connect() as db:
            db.execute("DELETE FROM messages WHERE account=? AND folder=? AND uid=?", (account, folder, uid))
