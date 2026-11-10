param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
& "$PSScriptRoot\build-core.ps1"
$python = Join-Path $root '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) {
    python -m venv "$root\.venv"
    & $python -m pip install -r "$root\requirements.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
}
Set-Location -LiteralPath $root
Write-Host "Open http://127.0.0.1:$Port . Press Ctrl+C to stop."
& $python -m uvicorn adviser.app:app --host 127.0.0.1 --port $Port
