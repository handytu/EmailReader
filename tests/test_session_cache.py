import tempfile
import sqlite3
import unittest
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from app.database.database import Database
from app.models.message import MailMessage
from app.models.account import EmailAccount, AccountState
from app.services.account_store import AccountStore
from app.ui.main_window import MainWindow


class SessionTests(unittest.TestCase):
    def test_old_database_is_migrated_without_losing_mail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old.db"
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE messages(account TEXT, folder TEXT, uid TEXT, sender_name TEXT, sender_addr TEXT, subject TEXT, date TEXT, preview TEXT, is_read INTEGER, is_starred INTEGER, PRIMARY KEY(account,folder,uid))")
            connection.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,?)", ("demo@example.com", "INBOX", "1", "Sender", "sender@example.com", "Legacy mail", "", "Preview", 0, 1))
            connection.commit()
            connection.close()
            messages = Database(path).load_messages("demo@example.com")
            self.assertEqual(messages[0].subject, "Legacy mail")
            self.assertTrue(messages[0].is_starred)
            self.assertEqual(messages[0].body_text, "")

    def test_full_mail_survives_database_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.db"
            message = MailMessage("1", body_html="<p>Complete email</p>", body_text="Complete email",
                                  date=datetime.now(timezone.utc), to_addrs=["demo@example.com"],
                                  attachments=[{"name": "report.pdf"}], is_starred=True)
            Database(path).cache_messages("demo@example.com", [message])
            self.assertEqual(Database(path).load_messages("demo@example.com"), [message])
            Database(path).cache_messages("demo@example.com", [])
            self.assertEqual(Database(path).load_messages("demo@example.com"), [])

    def test_accounts_persist_encrypted_in_original_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "accounts.bin"
            accounts = {email: EmailAccount(email, password="secret-password", refresh_token="secret-token")
                        for email in ("second@example.com", "first@example.com")}
            AccountStore(path).save(accounts)
            self.assertNotIn(b"secret-password", path.read_bytes())
            self.assertNotIn(b"secret-token", path.read_bytes())
            restored = AccountStore(path).load()
            self.assertEqual(list(restored), list(accounts))
            self.assertEqual(restored["first@example.com"].refresh_token, "secret-token")
            AccountStore(path).save({})
            self.assertEqual(AccountStore(path).load(), {})

    def test_refresh_only_selected_connected_account(self):
        account = EmailAccount("demo@example.com", state=AccountState.CONNECTED)
        window = SimpleNamespace(_closing=False, app_settings=SimpleNamespace(auto_refresh=True),
                                 accounts={account.email: account}, current_email=account.email,
                                 action_threads=set(), _fetch=Mock())
        MainWindow._auto_refresh_current(window)
        window._fetch.assert_called_once_with(account)
        for selected, state, busy in (("__all__", AccountState.CONNECTED, False),
                                      (account.email, AccountState.CONNECTING, False),
                                      (account.email, AccountState.AUTH_FAILED, False),
                                      (account.email, AccountState.CONNECTED, True)):
            window._fetch.reset_mock()
            window.current_email = selected
            account.state = state
            window.action_threads = {1} if busy else set()
            MainWindow._auto_refresh_current(window)
            window._fetch.assert_not_called()

    def test_fetch_does_not_overlap(self):
        account = EmailAccount("demo@example.com")
        window = SimpleNamespace(_closing=False, fetching={account.email})
        # Any attempted worker construction would fail: this harness has no Qt objects.
        MainWindow._fetch(window, account)


if __name__ == "__main__":
    unittest.main()
