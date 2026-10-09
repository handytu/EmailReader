# EmailReader

**English** | [Tiếng Việt](README.vi.md)

Multi-account email reader for Windows, built with Python and PySide6.

## Main features

- Supports Outlook/Hotmail, Gmail, Yahoo and custom IMAP servers.
- Add individual accounts or import an account list from a TXT file.
- Read HTML emails, search messages and copy verification codes.
- Save accounts and cached mail, and restore your session on startup.
- Automatically refresh the current account every 10 seconds.
- Dark interface, customizable app name colors and optional remote image blocking.
- Press **Ctrl + W** to close the app.

## Run from source

Requires Windows and Python 3.11.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Add accounts

Select **Add accounts → Add single account**, or import a TXT file using this format:

```text
email@example.com|password
```

Outlook supports Microsoft device code sign-in. For Gmail/Yahoo, use an app password when required by your provider.

## Build a Windows executable with Nuitka

```powershell
py -3.11 -m venv .build-venv
.build-venv\Scripts\python.exe -m pip install -r requirements.txt nuitka ordered-set zstandard
powershell -ExecutionPolicy Bypass -File .\build-nuitka.ps1
```

Build output is in `release/nuitka-*/main.dist/`. Keep the entire folder together when running `EmailReader.exe`.

## Data

Accounts and cached mail are stored in the `data` folder beside the app. Credentials are protected with Windows DPAPI and tied to the current Windows user. Keep the `data` folder when upgrading to preserve your session.

Account files, cached mail, logs and build outputs are excluded from Git by `.gitignore`.
