"""Package a Nuitka distribution without personal session files."""
import sys
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.version import VERSION

distribution = Path(sys.argv[1]).resolve()
target = Path('release') / f'EmailReader-v{VERSION}-Nuitka.zip'
assert (distribution / 'EmailReader.exe').is_file()
excluded = {'data', 'logs', '__pycache__'}
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for item in distribution.rglob('*'):
        relative = item.relative_to(distribution)
        if item.is_file() and not excluded.intersection(relative.parts):
            archive.write(item, 'EmailReader/' + relative.as_posix())
    archive.writestr('EmailReader/UPGRADE.txt',
        f'EmailReader v{VERSION}\n\n'
        'Extract the complete folder before opening EmailReader.exe.\n'
        'Close your old app and copy its data folder beside the new exe to preserve accounts and cached mail.\n'
        'Keep all DLLs and support folders together. Keep your old build as a backup.\n'
        'Accounts encrypted with Windows DPAPI must be opened by the same Windows user on the same computer.\n'
        'Add accounts > Add single account adds an account without importing TXT.\n'
        'Settings lets you change the Email and Reader text colors separately.\n')
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
    assert not any(Path(name).suffix in {'.py', '.pyc', '.db'} or
                   Path(name).name in {'emails.txt', 'accounts.bin'} for name in archive.namelist())
print(f'Verified: {target.resolve()} ({target.stat().st_size / 1024**2:.1f} MB)')
