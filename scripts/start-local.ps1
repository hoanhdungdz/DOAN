$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskLogs = Join-Path $taskRoot '.runtime'
New-Item -ItemType Directory -Path $taskLogs -Force | Out-Null
function Test-TaskPort([int]$Port) {
    $taskClient = [System.Net.Sockets.TcpClient]::new()
    try { $taskClient.Connect('127.0.0.1', $Port); return $true }
    catch { return $false }
    finally { $taskClient.Dispose() }
}
$taskMysqlData = Join-Path $env:LOCALAPPDATA 'TechRetailRuntime\mysql'
if ((Test-Path -LiteralPath $taskMysqlData) -and !(Test-TaskPort 3307)) {
    $taskMysqlExe = 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe'
    Start-Process -FilePath $taskMysqlExe -WorkingDirectory $env:LOCALAPPDATA -WindowStyle Hidden -ArgumentList @('--no-defaults', "--datadir=$taskMysqlData", '--port=3307', '--bind-address=127.0.0.1', '--mysqlx=OFF') -RedirectStandardError (Join-Path $taskLogs 'mysql.log') | Out-Null
    Write-Host 'Started isolated MySQL on 3307; existing MySQL service is untouched.'
}
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $taskPython)) { throw 'Create .venv and install requirements first (README.md).' }
if (!(Test-TaskPort 8000)) {
    Start-Process -FilePath $taskPython -WorkingDirectory (Join-Path $taskRoot 'be') -WindowStyle Hidden -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8000', '--noreload') -RedirectStandardOutput (Join-Path $taskLogs 'backend.log') -RedirectStandardError (Join-Path $taskLogs 'backend-error.log') | Out-Null
}
$taskNode = (Get-Command node.exe).Source
$taskVite = Join-Path $taskRoot 'node_modules\vite\bin\vite.js'
foreach ($taskApp in @(@('fe',5173), @('admin',5174))) {
    if (!(Test-TaskPort $taskApp[1])) {
        Start-Process -FilePath $taskNode -WorkingDirectory (Join-Path $taskRoot $taskApp[0]) -WindowStyle Hidden -ArgumentList @(('"' + $taskVite + '"'), '--host', '127.0.0.1', '--port', $taskApp[1], '--strictPort') -RedirectStandardOutput (Join-Path $taskLogs ($taskApp[0]+'.log')) -RedirectStandardError (Join-Path $taskLogs ($taskApp[0]+'-error.log')) | Out-Null
    }
}
Write-Host 'Customer: http://127.0.0.1:5173 | Staff: http://127.0.0.1:5174 | API: http://127.0.0.1:8000'
Write-Host 'Development only. Logs in .runtime. Run be/manage.py expire_reservations every minute.'
