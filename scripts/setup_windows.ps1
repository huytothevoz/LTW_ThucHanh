# Set up the Laravel web backend and isolated Python crawler environment.
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
            $env:PATH = "$(Split-Path $Candidate -Parent);$env:PATH"
            break
        }
    }
}
$Composer = Get-Command composer -ErrorAction SilentlyContinue
if (-not $Composer) {
    $LocalComposer = Join-Path $env:LOCALAPPDATA 'Programs\Composer\composer.bat'
    if (Test-Path $LocalComposer) {
        $Composer = Get-Item $LocalComposer
        $env:PATH = "$(Split-Path $LocalComposer -Parent);$env:PATH"
    }
}
if (-not $Php) { throw 'PHP 8.2+ was not found. Install PHP or add its folder to PATH (for XAMPP, usually C:\xampp\php).' }
if (-not $Composer) { throw 'Composer was not found. Install Composer from https://getcomposer.org/download/ and reopen this window.' }
$PhpExe = $Php.Source
if (-not $PhpExe) { $PhpExe = $Php.FullName }
if (-not $PhpExe) { $PhpExe = $Php.Path }
& $PhpExe -r 'exit(PHP_VERSION_ID >= 80200 ? 0 : 1);'
if ($LASTEXITCODE -ne 0) { throw 'PHP 8.2 or newer is required.' }
$PhpModules = & $PhpExe -m
if ($LASTEXITCODE -ne 0) { throw 'Could not read PHP modules. Check the selected PHP installation.' }
if ($PhpModules -notcontains 'pdo_mysql') {
    throw "PHP PDO MySQL is not enabled in '$PhpExe'. Enable pdo_mysql in that PHP installation's php.ini and restart setup."
}

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
}

function Get-DotEnvValue([string]$Name) {
    $Line = Get-Content '.env' -Encoding UTF8 | Where-Object { $_ -match ('^' + [regex]::Escape($Name) + '=') } | Select-Object -First 1
    if (-not $Line) { return '' }
    return ($Line -split '=', 2)[1].Trim().Trim('"').Trim("'")
}

function Set-DotEnvValue([string]$Name, [string]$Value, [bool]$Replace = $false) {
    $StoredValue = $Value
    if ($StoredValue -match '\s' -and -not ($StoredValue.StartsWith("'") -and $StoredValue.EndsWith("'"))) {
        $StoredValue = "'$StoredValue'"
    }
    $Lines = New-Object 'System.Collections.Generic.List[string]'
    foreach ($ExistingLine in (Get-Content '.env' -Encoding UTF8)) { $Lines.Add($ExistingLine) }
    $Found = $false
    for ($Index = 0; $Index -lt $Lines.Count; $Index++) {
        if ($Lines[$Index] -match ('^' + [regex]::Escape($Name) + '=')) {
            $Found = $true
            $Current = ($Lines[$Index] -split '=', 2)[1].Trim().Trim('"').Trim("'")
            if ($Replace -or [string]::IsNullOrWhiteSpace($Current)) {
                $Lines[$Index] = "$Name=$StoredValue"
            }
        }
    }
    if (-not $Found) { $Lines.Add("$Name=$StoredValue") }
    [System.IO.File]::WriteAllLines(
        (Join-Path $Root '.env'),
        $Lines,
        [System.Text.UTF8Encoding]::new($false)
    )
}

$PreviousConnection = Get-DotEnvValue 'DB_CONNECTION'
if ($PreviousConnection -eq 'sqlite' -or [string]::IsNullOrWhiteSpace($PreviousConnection)) {
    Set-DotEnvValue 'DB_CONNECTION' 'mysql' $true
}
Set-DotEnvValue 'DB_HOST' '127.0.0.1'
Set-DotEnvValue 'DB_PORT' '3306' $true
Set-DotEnvValue 'DB_DATABASE' 'crawlinsight'
Set-DotEnvValue 'DB_USERNAME' 'root'
Set-DotEnvValue 'DB_PASSWORD' '' $true

$LegacySqlitePath = Get-DotEnvValue 'CRAWLINSIGHT_SQLITE_IMPORT'
if ([string]::IsNullOrWhiteSpace($LegacySqlitePath)) {
    $LegacySqlitePath = Get-DotEnvValue 'CRAWLINSIGHT_DB_PATH'
}
if ([string]::IsNullOrWhiteSpace($LegacySqlitePath)) {
    if ((Split-Path (Split-Path $Root -Parent) -Leaf) -ieq 'htdocs') {
        $LegacySqlitePath = Join-Path (Split-Path (Split-Path $Root -Parent) -Parent) 'ltw-th-private-data\crawlinsight.db'
    }
    else {
        $LegacySqlitePath = Join-Path $Root 'data\crawlinsight.db'
    }
}
if ([System.IO.Path]::IsPathRooted($LegacySqlitePath) -and $LegacySqlitePath.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)) {
    $LegacySqlitePath = $LegacySqlitePath.Substring($Root.Length).TrimStart('\', '/')
}
Set-DotEnvValue 'CRAWLINSIGHT_SQLITE_IMPORT' $LegacySqlitePath

Write-Host 'Installing Laravel dependencies ...' -ForegroundColor Cyan
$ComposerCommand = $Composer.Source
if (-not $ComposerCommand) { $ComposerCommand = $Composer.Path }
if (-not $ComposerCommand) { $ComposerCommand = $Composer.FullName }
& $ComposerCommand install --no-interaction --prefer-dist
if ($LASTEXITCODE -ne 0) { throw 'Composer dependency installation failed.' }

$AppKeyLine = Get-Content '.env' -Encoding UTF8 | Where-Object { $_ -match '^APP_KEY=' } | Select-Object -First 1
if (-not $AppKeyLine -or $AppKeyLine -eq 'APP_KEY=') {
    & $PhpExe artisan key:generate --no-interaction
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate the Laravel application key.' }
}

$PythonOverride = Get-DotEnvValue 'CRAWLINSIGHT_PYTHON'
$Python = $null

if (-not [string]::IsNullOrWhiteSpace($PythonOverride)) {
    $Python = $PythonOverride.Trim()
    if (-not (Test-Path $Python)) {
        throw "CRAWLINSIGHT_PYTHON points to a missing Python executable: $Python"
    }
    & $Python -c 'import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'CRAWLINSIGHT_PYTHON must point to Python 3.11 or 3.12.' }
}
else {
    $PythonLauncher = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($Version in @('-3.12', '-3.11')) {
            & py $Version --version *> $null
            if ($LASTEXITCODE -eq 0) { $PythonLauncher = @('py', $Version); break }
        }
    }
    if (-not $PythonLauncher) {
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            throw 'Python 3.11 or 3.12 is required for the crawler.'
        }
        & python -c 'import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)'
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or 3.12 is required for the crawler.' }
        $PythonLauncher = @('python')
    }

    $Python = Join-Path $Root '.venv\Scripts\python.exe'
    if (-not (Test-Path $Python)) {
        if ($PythonLauncher.Count -eq 2) { & $PythonLauncher[0] $PythonLauncher[1] -m venv .venv }
        else { & $PythonLauncher[0] -m venv .venv }
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the crawler virtual environment.' }
    }

    & $Python -c 'import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)'
    if ($LASTEXITCODE -ne 0) {
        Remove-Item '.venv' -Recurse -Force -ErrorAction SilentlyContinue
        if ($PythonLauncher.Count -eq 2) { & $PythonLauncher[0] $PythonLauncher[1] -m venv .venv }
        else { & $PythonLauncher[0] -m venv .venv }
        if ($LASTEXITCODE -ne 0) { throw 'Could not repair the crawler virtual environment.' }
        $Python = Join-Path $Root '.venv\Scripts\python.exe'
    }
}

$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Crawler dependency installation failed.' }

foreach ($Line in (Get-Content '.env' -Encoding UTF8)) {
    if ($Line -match '^\s*([^#=\s]+)=(.*)$') {
        $Name = $Matches[1]
        $Value = $Matches[2].Trim().Trim('"').Trim("'")
        if ($Value.Length -le 32000) {
            [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
        }
    }
}

function Get-MySqlServerVersion([string]$HostName, [int]$Port) {
    $Client = New-Object System.Net.Sockets.TcpClient
    try {
        $Client.ReceiveTimeout = 2000
        $Client.SendTimeout = 2000
        $Client.Connect($HostName, $Port)
        $Stream = $Client.GetStream()
        $Header = New-Object byte[] 4
        $HeaderBytesRead = 0
        while ($HeaderBytesRead -lt $Header.Length) {
            $Read = $Stream.Read($Header, $HeaderBytesRead, $Header.Length - $HeaderBytesRead)
            if ($Read -le 0) { return $null }
            $HeaderBytesRead += $Read
        }

        $PacketLength = [int]$Header[0] + ([int]$Header[1] -shl 8) + ([int]$Header[2] -shl 16)
        if ($PacketLength -lt 2 -or $PacketLength -gt 65536) { return $null }
        $Packet = New-Object byte[] $PacketLength
        $PacketBytesRead = 0
        while ($PacketBytesRead -lt $Packet.Length) {
            $Read = $Stream.Read($Packet, $PacketBytesRead, $Packet.Length - $PacketBytesRead)
            if ($Read -le 0) { return $null }
            $PacketBytesRead += $Read
        }

        if ($Packet[0] -ne 10) { return $null }
        $VersionEnd = [Array]::IndexOf($Packet, [byte]0, 1)
        if ($VersionEnd -lt 2) { return $null }
        return [System.Text.Encoding]::ASCII.GetString($Packet, 1, $VersionEnd - 1)
    }
    catch [System.Net.Sockets.SocketException] {
        return $null
    }
    catch [System.IO.IOException] {
        return $null
    }
    finally {
        $Client.Close()
    }
}

$XamppRoots = New-Object 'System.Collections.Generic.List[string]'
if ($env:XAMPP_HOME) { $XamppRoots.Add($env:XAMPP_HOME) }
$PhpDirectory = Split-Path $PhpExe -Parent
if ((Split-Path $PhpDirectory -Leaf) -ieq 'php') {
    $XamppRoots.Add((Split-Path $PhpDirectory -Parent))
}
$XamppRoots.Add((Join-Path $env:SystemDrive 'xampp'))

$XamppRoot = $null
foreach ($CandidateRoot in ($XamppRoots | Select-Object -Unique)) {
    if (Test-Path (Join-Path $CandidateRoot 'mysql\bin\mysqld.exe')) {
        $XamppRoot = $CandidateRoot
        break
    }
}
if (-not $XamppRoot) {
    throw 'XAMPP MariaDB was not found. Install XAMPP or set XAMPP_HOME to its installation folder.'
}

$MysqlDirectory = Join-Path $XamppRoot 'mysql\bin'
$MysqlServer = Join-Path $MysqlDirectory 'mysqld.exe'
$MysqlIni = Join-Path $MysqlDirectory 'my.ini'
if (-not (Test-Path $MysqlIni)) { throw "XAMPP MySQL configuration was not found: $MysqlIni" }

$RequestedPort = $env:DB_PORT
if ([string]::IsNullOrWhiteSpace($RequestedPort) -or [int]$RequestedPort -lt 1 -or [int]$RequestedPort -gt 65535) {
    throw "Invalid DB_PORT '$RequestedPort' in .env."
}

$ExistingServerVersion = Get-MySqlServerVersion $env:DB_HOST ([int]$RequestedPort)
if ($ExistingServerVersion -and $ExistingServerVersion -notmatch 'MariaDB') {
    throw "Port $RequestedPort is occupied by '$ExistingServerVersion', not XAMPP MariaDB. Stop or reconfigure that separate service, then run START_HERE.bat again."
}

if (-not $ExistingServerVersion) {
    $XamppDefaultPort = $null
    $InMySqlSection = $false
    foreach ($IniLine in (Get-Content $MysqlIni -Encoding UTF8)) {
        if ($IniLine -match '^\s*\[mysqld\]\s*$') {
            $InMySqlSection = $true
            continue
        }
        if ($IniLine -match '^\s*\[') {
            $InMySqlSection = $false
            continue
        }
        if ($InMySqlSection -and $IniLine -match '^\s*port\s*=\s*(\d+)') {
            $XamppDefaultPort = [int]$Matches[1]
            break
        }
    }

    if ($XamppDefaultPort -and $XamppDefaultPort -ne [int]$RequestedPort) {
        $XamppProcesses = Get-CimInstance Win32_Process -Filter "Name='mysqld.exe'" -ErrorAction Stop |
            Where-Object {
                $_.ExecutablePath -and
                $_.ExecutablePath.Equals($MysqlServer, [System.StringComparison]::OrdinalIgnoreCase) -and
                $_.CommandLine -and
                $_.CommandLine.IndexOf($MysqlIni, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
            }
        if ($XamppProcesses) {
            $XamppDefaultVersion = Get-MySqlServerVersion $env:DB_HOST $XamppDefaultPort
            if ($XamppDefaultVersion -and $XamppDefaultVersion -match 'MariaDB') {
                $RequestedPort = "$XamppDefaultPort"
                $env:DB_PORT = $RequestedPort
                Set-DotEnvValue 'DB_PORT' $RequestedPort $true
                $ExistingServerVersion = $XamppDefaultVersion
                Write-Host "Reusing the running XAMPP MariaDB on its configured port $RequestedPort to avoid starting a second server against the same data directory." -ForegroundColor Green
            }
            elseif (-not $XamppDefaultVersion) {
                throw "XAMPP mysqld is already running with '$MysqlIni' but is not accepting connections on port $XamppDefaultPort. Stop that XAMPP MariaDB instance or check its logs before retrying; setup will not start a second server against the same data directory."
            }
            else {
                throw "XAMPP mysqld is already running, but port $XamppDefaultPort responds as '$XamppDefaultVersion'. Stop or inspect that server before retrying."
            }
        }
    }
}

if ($ExistingServerVersion) {
    Write-Host "Reusing XAMPP MariaDB $ExistingServerVersion on $env:DB_HOST`:$RequestedPort." -ForegroundColor Green
}
else {
    Write-Host "Starting XAMPP MariaDB on $env:DB_HOST`:$RequestedPort ..." -ForegroundColor Cyan
    $LogDirectory = Join-Path $Root 'storage\logs'
    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    $MysqlStdout = Join-Path $LogDirectory 'mysql-startup.log'
    $MysqlStderr = Join-Path $LogDirectory 'mysql-startup-error.log'
    $MysqlArguments = "--defaults-file=`"$MysqlIni`" --port=$RequestedPort --console"
    $MysqlProcess = Start-Process `
        -FilePath $MysqlServer `
        -ArgumentList $MysqlArguments `
        -WorkingDirectory $MysqlDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $MysqlStdout `
        -RedirectStandardError $MysqlStderr `
        -PassThru

    $MysqlReady = $false
    for ($Attempt = 0; $Attempt -lt 60; $Attempt++) {
        Start-Sleep -Seconds 1
        $StartedServerVersion = Get-MySqlServerVersion $env:DB_HOST ([int]$RequestedPort)
        if ($StartedServerVersion -and $StartedServerVersion -match 'MariaDB') {
            $MysqlReady = $true
            break
        }
        if ($MysqlProcess.HasExited) { break }
    }
    if (-not $MysqlReady) {
        if ($StartedServerVersion) {
            throw "Port $RequestedPort is occupied by '$StartedServerVersion', not XAMPP MariaDB. Startup output is in storage\logs."
        }
        $StartupDetails = @()
        foreach ($LogPath in @($MysqlStderr, $MysqlStdout)) {
            if (Test-Path $LogPath) {
                $StartupDetails += Get-Content $LogPath -Tail 12
            }
        }
        $Details = $StartupDetails -join [Environment]::NewLine
        if (-not $Details) { $Details = 'No MySQL startup log was produced.' }
        throw "XAMPP MariaDB did not become ready on port $RequestedPort. Startup output:`n$Details"
    }
    Write-Host "XAMPP MariaDB started successfully on port $RequestedPort." -ForegroundColor Green
}

Write-Host "Creating/updating MySQL database '$env:DB_DATABASE' on $env:DB_HOST`:$RequestedPort and importing legacy SQLite data if present ..."
& $Python -c 'from src.db import init_db; init_db()'
if ($LASTEXITCODE -ne 0) {
    throw 'MySQL initialization failed. Check the XAMPP MariaDB startup logs in storage\logs and confirm the XAMPP root account allows local login without a password.'
}

Write-Host 'Database setup complete. START_HERE.bat will now start Laravel.' -ForegroundColor Green
