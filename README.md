# EmailReader v9.4.2

## Recent updates

- Dark mountain placeholder replaces the bright empty reading pane at startup.
- Verification code extraction prioritizes explicit subject/body labels and preserves leading zeros.
- Add one account directly from Add accounts, without importing a TXT file.
- Calibri Bold app name with independently configurable Email/Reader colors in Settings.
- Windows executable builds use Nuitka; run `build-nuitka.ps1` to build and preserve a source backup.
- Personal account files, mail cache, local environments and build outputs are excluded by `.gitignore`.

## v9.3.0 — Tabs identity and Mountains title bar

- Tabs icon in the application and Windows executable, with multiple icon sizes.
- Mountain background replaces the native white title bar.
- Native system move/resize from the title bar and window edges; double-click
  toggles maximized state. Minimize, maximize/restore and close buttons remain accessible.
- Right-click the title bar for window controls. Ctrl+W still closes the app.
- Session cache and 10-second refresh settings remain compatible.
- UI controls check: `python tests/check_titlebar_ui.py`.

## v9.2.1 — fast close

- Ctrl+W closes the application, including while a mailbox task is running.
- Closing hides the window immediately and cancels pending background work.
- A blocked network operation cannot keep the app running indefinitely: shutdown
  has a two-second deadline. Completed cache writes remain on disk.
- Microsoft device-login polling responds to cancellation without waiting for
  the next polling interval.
- Process-level close checks: `python tests/check_close_ui.py`.

## v9.2.0 — restored sessions and live inbox

- Imported accounts persist automatically, in their original order. Windows DPAPI
  protects the saved account credentials for the current Windows user.
- On restart, the last selected account opens with all previously loaded inboxes
  available locally, including plain text, HTML, recipients and attachment metadata.
- The current account refreshes every 10 seconds after connecting; other accounts
  are not automatically synced. Overlapping refreshes are skipped.
- Turn automatic refresh off in Settings. Authentication failures require manual reconnect.
- Keep the `data` folder beside the exe when upgrading to retain your session.
  Older versions did not save the imported account list or full email bodies;
  import and sync once in v9.2.0 to create the complete cache.
- Account protection is Windows-user-bound; moving to another Windows user or PC
  may require reimporting the original account file.
- Offline restore integration check: `python tests/check_session_ui.py`.

## Reader and search improvements

- Desktop UI uses larger controls, readable secondary text, and visible keyboard focus.
- Icon buttons have accessible names; account status is shown in text as well as color.
- Press Enter to open a focused account; compact message rows show sender and subject.
- Verification codes fit the reader at the minimum desktop window width.
- See `DESIGN_SYSTEM.md` for the design rules. Render fictional-data previews with
  `python tests/preview_ui.py` (Windows fonts; no mailbox connection).

- Search loaded mail by sender, subject, preview, plain-text body, recipient, or source account.
- Global search stays active when an inbox syncs or a message action completes.
- Refreshes preserve selection by account, folder, and message ID; filtering out a message clears its reader.
- All Inboxes updates its unread count after sync and read-state changes.
- Search fields have clear buttons; Ctrl+Shift+F focuses global search.
- The filter toolbar button opens a working filter menu, with clearer empty-list messages.
- Removing an account also removes its loaded mail from global results.

Run regression checks with `python -m unittest discover -s tests -v`.

## Changes in v8

- Removed Reply, Reply All and Forward from the message toolbar.
- Removed Reply/Forward actions from the mail right-click menu.
- Settings button is now active and opens a real persistent Settings dialog.
- Settings are stored in `data/settings.json`.
- Functional settings:
  - Messages per load: 25 / 50 / 100.
  - Message density: Comfortable / Compact.
  - Block remote images by default.
  - Confirm before deleting email.
  - Open the last selected account at startup.
- Changing density updates the inbox immediately.
- Remote-image privacy setting is applied to the currently opened email immediately.
- Account order remains exactly the same as `emails.txt`.
- Microsoft inbox login keeps the stable `offline_access Mail.ReadWrite` scope from v7.

Desktop multi-account email reader built with Python + PySide6.

## v6 changes

- Account sidebar now preserves the exact order from `emails.txt`.
- Removed automatic provider sorting/grouping that changed account order.
- Reply, Reply All and Forward buttons now open an in-app compose window.
- Star button now updates the real mailbox state.
- Delete button now deletes the real message after confirmation.
- More menu now supports Mark as Read/Unread, Copy sender and Copy subject.
- Mail right-click menu uses the same live actions.
- Microsoft Graph send support added with `Mail.Send` permission when available.
- Gmail/Yahoo/custom IMAP accounts can send through SMTP when provider credentials allow it (Gmail/Yahoo often require an app password).
- Message parser now keeps To/Cc/Reply-To so Reply All can build recipients correctly.

## Run

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Build Windows

```bat
build.bat
```

Output is under `release/EmailReader/`.

## emails.txt

Basic:

```text
email@example.com|password
```

Microsoft OAuth:

```text
email@outlook.com|password|refresh_token|client_id
```

Optional proxy:

```text
email@outlook.com|password|refresh_token|client_id|http://user:pass@host:port
```

The account order shown in the app follows the file from top to bottom.
## v9 - Microsoft Device Login fallback

For Outlook / Hotmail / Live accounts, EmailReader keeps the existing authentication path first. If Microsoft blocks the password web-flow because of MFA, CAPTCHA, identity confirmation, or changed login pages, the app now falls back to Microsoft's Device Code flow.

The app opens the official Microsoft sign-in page and shows the one-time code in a desktop dialog. Complete the sign-in in the browser; the background worker then continues loading the inbox automatically.

You can also right-click an Outlook account and choose **Sign in with Microsoft code** to force this flow manually.

Device login uses the official Microsoft OAuth device-code endpoints directly and requires no extra authentication package.
