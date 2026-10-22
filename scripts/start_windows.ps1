# Start Laravel locally. Keep this terminal open while using CrawlInsight.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
$Php = Get-Command php -ErrorAction SilentlyContinue
if (-not $Php) {
    $PhpCandidates = @(
        (Join-Path $env:SystemDrive 'xampp\php\php.exe'),
        (Join-Path $env:SystemDrive 'laragon\bin\php\php.exe')
    )
    foreach ($Candidate in $PhpCandidates) {
        if (Test-Path $Candidate) {
            $Php = Get-Item $Candidate
            break
        }
    }
}
if (-not $Php) { throw 'PHP 8.2+ was not found. Install PHP or add its folder to PATH (for XAMPP, usually C:\xampp\php).' }
$PhpExe = $Php.Source
if (-not $PhpExe) { $PhpExe = $Php.FullName }
if (-not $PhpExe) { $PhpExe = $Php.Path }
$PhpVersion = & $PhpExe -r 'echo PHP_VERSION_ID;'
if ($LASTEXITCODE -ne 0 -or [int]$PhpVersion -lt 80200) { throw 'PHP 8.2 or newer is required.' }
if (-not (Test-Path 'vendor/autoload.php')) { throw 'Missing vendor dependencies. Run scripts/setup_windows.ps1 first.' }
if (-not (Test-Path '.env')) { throw 'Missing .env. Run scripts/setup_windows.ps1 first.' }
Write-Host 'Starting Laravel at http://127.0.0.1:8000/' -ForegroundColor Cyan
& $PhpExe artisan serve --host=127.0.0.1 --port=8000
