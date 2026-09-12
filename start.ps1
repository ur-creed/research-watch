$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "Missing .venv. Create it with Python 3.12: py -3.12 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e `".[dev]`""
}
& $py web_server.py @args
