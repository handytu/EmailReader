import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QListView

from app.models.account import EmailAccount
from app.models.message import MailMessage
from app.ui.models import AccountListModel, MailListModel, MailRow, ROLE_MESSAGE
from app.ui.main_window import MainWindow


class ViewHarness:
    _refresh_mail_view = MainWindow._refresh_mail_view
    _update_list_empty = MainWindow._update_list_empty

    def __init__(self):
        self.current_email = "first@example.com"
        self.current_source_email = self.current_email
        self.current_message = None
        self.filter_mode = "all"
        self.messages = {}
        self.global_search = QLineEdit()
        self.search = QLineEdit()
        self.inbox_title = QLabel()
        self.inbox_account = QLabel()
        self.list_empty = QLabel()
        self.mail_model = MailListModel()
        self.mail_list = QListView()
        self.mail_list.setModel(self.mail_model)

    def _show_empty_reader(self):
        self.current_message = None
        self.current_source_email = ""


class MailViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_search_includes_body_recipients_and_source(self):
        model = MailListModel()
        message = MailMessage("1", body_text="Your unique code: 654321",
                              to_addrs=["recipient@example.com"])
        model.set_messages([MailRow(message, "source@example.com", 0)])
        for query in ("654321", "RECIPIENT@EXAMPLE.COM", "source@example.com"):
            model.set_filter(query)
            self.assertEqual(model.rowCount(), 1)
        model.set_filter("unmatched")
        self.assertEqual(model.rowCount(), 0)

    def test_global_search_survives_refresh_and_restores_header(self):
        view = ViewHarness()
        view.messages = {view.current_email: [MailMessage("1", subject="Other")],
                         "second@example.com": [MailMessage("2", subject="Code")]}
        view.global_search.setText("Code")
        view._refresh_mail_view()
        self.assertEqual(view.mail_model.rowCount(), 1)
        view.messages["second@example.com"].append(MailMessage("3", subject="Code again"))
        view._refresh_mail_view()
        self.assertEqual(view.mail_model.rowCount(), 2)
        self.assertEqual(view.inbox_title.text(), "Search")
        view.global_search.clear()
        view._refresh_mail_view()
        self.assertEqual(view.inbox_title.text(), "Inbox")
        self.assertEqual(view.inbox_account.text(), view.current_email)
        self.assertEqual(view.mail_model.rows[0].message.uid, "1")

    def test_selection_restored_by_source_folder_and_uid(self):
        view = ViewHarness()
        view.current_email = "__all__"
        message = MailMessage("same")
        view.messages = {"first@example.com": [MailMessage("same")],
                         "second@example.com": [message]}
        view.current_source_email = "second@example.com"
        view.current_message = message
        view._refresh_mail_view()
        self.assertIs(view.mail_list.currentIndex().data(ROLE_MESSAGE), message)
        view.search.setText("missing")
        view._refresh_mail_view()
        self.assertIsNone(view.current_message)
        self.assertIn("match", view.list_empty.text())

    def test_all_inboxes_unread_count_updates(self):
        model = AccountListModel()
        account = EmailAccount(email="first@example.com", password="")
        model.set_accounts({account.email: account})
        account.unread = 3
        model.refresh_account(account.email)
        self.assertEqual(model.rows[0].count, 3)


if __name__ == "__main__":
    unittest.main()
