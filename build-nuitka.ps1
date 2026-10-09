$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$buildPython = Join-Path $PSScriptRoot '.build-venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $buildPython)) {
    throw 'Missing build environment. Create .build-venv and install requirements.txt plus Nuitka, ordered-set and zstandard.'
}
$buildStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
New-Item -ItemType Directory -Path 'backups' -Force | Out-Null
Compress-Archive -LiteralPath app,resources,tests,main.py,build.bat,build-nuitka.ps1,requirements.txt,README.md,DESIGN_SYSTEM.md -DestinationPath ('backups/source-' + $buildStamp + '.zip')
$buildOutput = 'release/nuitka-' + $buildStamp
$appVersion = & $buildPython -c "from app.version import VERSION; print(VERSION)"
if ($LASTEXITCODE -ne 0) { throw 'Could not read application version.' }
& $buildPython -m nuitka --mode=standalone --enable-plugin=pyside6 --include-data-dir=resources=resources --windows-console-mode=disable --windows-icon-from-ico=resources/app-icon.ico --product-name=EmailReader "--product-version=$appVersion" "--file-version=$appVersion" --file-description=EmailReader --mingw64 --assume-yes-for-downloads "--output-dir=$buildOutput" --output-filename=EmailReader.exe "--report=$buildOutput-report.xml" main.py
if ($LASTEXITCODE -ne 0) { throw 'Nuitka build failed. Source backup is preserved.' }
Write-Output "Built: $buildOutput/main.dist/EmailReader.exe"
Write-Output 'Keep the complete main.dist folder together. Account files and cached email are not bundled.'
