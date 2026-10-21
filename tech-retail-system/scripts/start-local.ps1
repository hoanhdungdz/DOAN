param(
    [ValidateRange(1, 120)][int]$StartupTimeoutSeconds = 45
)

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskLogs = Join-Path $taskRoot '.runtime'
New-Item -ItemType Directory -Path $taskLogs -Force | Out-Null

function Test-TaskPort([string]$HostName, [int]$Port) {
    $taskClient = [System.Net.Sockets.TcpClient]::new()
    try {
        $taskConnection = $taskClient.ConnectAsync($HostName, $Port)
        if (!$taskConnection.Wait(500)) { return $false }
        return $taskClient.Connected
    }
    catch { return $false }
    finally { $taskClient.Dispose() }
}

function Wait-TaskReady {
    param([string]$Name, [scriptblock]$Probe, [System.Diagnostics.Process]$StartedProcess, [string]$LogPath)
    $taskTimer = [System.Diagnostics.Stopwatch]::StartNew()
    while ($taskTimer.Elapsed.TotalSeconds -lt $StartupTimeoutSeconds) {
        if ($StartedProcess) {
            $StartedProcess.Refresh()
            if ($StartedProcess.HasExited) {
                throw "$Name exited with code $($StartedProcess.ExitCode). See $LogPath"
            }
        }
        if (& $Probe) { Write-Host "$Name is ready."; return }
        Start-Sleep -Milliseconds 300
    }
    throw "$Name was not ready after $StartupTimeoutSeconds seconds. See $LogPath"
}

function Test-TaskJson([string]$Url, [string]$RequiredProperty) {
    try {
        $taskResponse = Invoke-RestMethod -Uri $Url -TimeoutSec 2 -ErrorAction Stop
        return $null -ne $taskResponse -and $taskResponse.PSObject.Properties.Name -contains $RequiredProperty
    }
    catch { return $false }
}

# Validate dependencies before starting any background process.
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
$taskEnv = Join-Path $taskRoot 'be\.env'
$taskVite = Join-Path $taskRoot 'node_modules\vite\bin\vite.js'
if (!(Test-Path -LiteralPath $taskPython)) { throw 'Create .venv and install Python requirements first (README.md).' }
if (!(Test-Path -LiteralPath $taskEnv)) { throw 'Configure be/.env first (README.md). Existing database configuration is never replaced.' }
if (!(Test-Path -LiteralPath $taskVite)) { throw 'Run npm.cmd ci from tech-retail-system first.' }
$taskNode = (Get-Command node.exe -ErrorAction Stop).Source

# Read only non-secret settings, using the same environment/configuration as Django.
$taskDbCode = @'
import os, json, sys
sys.path.insert(0, sys.argv[1])
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
d = settings.DATABASES['default']
print(json.dumps({'host': d['HOST'], 'port': int(d['PORT'] or 3306)}))
'@
$taskDbJson = $taskDbCode | & $taskPython - (Join-Path $taskRoot 'be')
if ($LASTEXITCODE -ne 0) { throw 'Cannot load Django configuration. Check be/.env and Python requirements.' }
$taskDb = $taskDbJson | ConvertFrom-Json
$taskMysqlProcess = $null
$taskMysqlLog = Join-Path $taskLogs 'mysql.log'

if (!(Test-TaskPort $taskDb.host $taskDb.port)) {
    if ($taskDb.host -in @('127.0.0.1', 'localhost') -and $taskDb.port -eq 3307) {
        $taskMysqlData = Join-Path $env:LOCALAPPDATA 'TechRetailRuntime\mysql'
        $taskMysqlExe = 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe'
        if (!(Test-Path -LiteralPath $taskMysqlData)) { throw "Isolated MySQL data not found: $taskMysqlData. Follow README.md setup; no database was recreated." }
        if (!(Test-Path -LiteralPath $taskMysqlExe)) { throw "MySQL executable not found: $taskMysqlExe. Start the database configured in be/.env." }
        Write-Host 'Starting isolated MySQL on 3307...'
        $taskMysqlProcess = Start-Process -FilePath $taskMysqlExe -WorkingDirectory $env:LOCALAPPDATA -WindowStyle Hidden -ArgumentList @('--no-defaults', ('--datadir="' + $taskMysqlData + '"'), '--port=3307', '--bind-address=127.0.0.1', '--mysqlx=OFF') -RedirectStandardError $taskMysqlLog -PassThru
    }
    else { Write-Host "Waiting for configured MySQL at $($taskDb.host):$($taskDb.port)..." }
}
Wait-TaskReady -Name "MySQL $($taskDb.host):$($taskDb.port)" -Probe { Test-TaskPort $taskDb.host $taskDb.port } -StartedProcess $taskMysqlProcess -LogPath $taskMysqlLog

$taskBackendProcess = $null
$taskBackendLog = Join-Path $taskLogs 'backend-error.log'
if (!(Test-TaskPort '127.0.0.1' 8000)) {
    Write-Host 'Starting Django backend...'
    $taskBackendProcess = Start-Process -FilePath $taskPython -WorkingDirectory (Join-Path $taskRoot 'be') -WindowStyle Hidden -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8000', '--noreload') -RedirectStandardOutput (Join-Path $taskLogs 'backend.log') -RedirectStandardError $taskBackendLog -PassThru
}
# A successful catalog request verifies HTTP, database access and schema together.
Wait-TaskReady -Name 'Backend API' -Probe { Test-TaskJson 'http://127.0.0.1:8000/api/v1/products/?page_size=1' 'results' } -StartedProcess $taskBackendProcess -LogPath $taskBackendLog

foreach ($taskApp in @(@('fe', 5173), @('admin', 5174))) {
    $taskFrontendProcess = $null
    $taskFrontendLog = Join-Path $taskLogs ($taskApp[0] + '-error.log')
    if (!(Test-TaskPort '127.0.0.1' $taskApp[1])) {
        Write-Host "Starting $($taskApp[0]) frontend..."
        $taskFrontendProcess = Start-Process -FilePath $taskNode -WorkingDirectory (Join-Path $taskRoot $taskApp[0]) -WindowStyle Hidden -ArgumentList @(('"' + $taskVite + '"'), '--host', '127.0.0.1', '--port', $taskApp[1], '--strictPort') -RedirectStandardOutput (Join-Path $taskLogs ($taskApp[0] + '.log')) -RedirectStandardError $taskFrontendLog -PassThru
    }
    # Probe IPv4 loopback directly; browser links below use localhost for OAuth.
    $taskFrontendUrl = "http://127.0.0.1:$($taskApp[1])"
    Wait-TaskReady -Name "$($taskApp[0]) frontend and API proxy" -Probe { Test-TaskJson ($taskFrontendUrl + '/api/v1/auth/me/') 'user' } -StartedProcess $taskFrontendProcess -LogPath $taskFrontendLog
}

Write-Host 'Ready: all services and API proxies responded successfully.'
Write-Host 'Customer: http://localhost:5173 | Staff: http://localhost:5174/login'
Write-Host 'API docs: http://localhost:8000/api/docs/'
Write-Host 'Development only. Logs in .runtime. Run be/manage.py expire_reservations every minute.'
