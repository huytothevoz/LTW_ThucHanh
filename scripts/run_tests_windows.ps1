$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
$Python = Join-Path $Root '.venv/Scripts/python.exe'
if (-not (Test-Path $Python)) { throw 'Missing crawler .venv. Run setup_windows.ps1 first.' }
if (-not (Test-Path 'vendor/autoload.php')) { throw 'Missing PHP dependencies. Run setup_windows.ps1 first.' }

& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Python crawler tests failed.' }
& composer test
if ($LASTEXITCODE -ne 0) { throw 'Laravel tests failed.' }
