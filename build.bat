@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (py -3.11 -m venv .venv)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm --clean --windowed --name EmailReader --icon resources\app-icon.ico --version-file resources\windows-version.txt --collect-all PySide6 --add-data "resources;resources" main.py
if not exist release mkdir release
if exist release\EmailReader rmdir /s /q release\EmailReader
xcopy /e /i /y dist\EmailReader release\EmailReader >nul
echo.
echo BUILD COMPLETE: %CD%\release\EmailReader\EmailReader.exe
pause
