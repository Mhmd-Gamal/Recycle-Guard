$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
& "$PSScriptRoot\build-core.ps1"
$stage = Join-Path $env:TEMP ('recycleguard-package-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
python -m PyInstaller --noconfirm --clean --onedir --name RecycleGuard --distpath "$stage\dist" --workpath "$stage\work" --specpath "$stage" --paths "$root" --add-data "$root\web;web" --add-binary "$root\build\RecycleGuard.Core.exe;build" --hidden-import uvicorn.logging --hidden-import uvicorn.loops.asyncio --hidden-import uvicorn.protocols.http.h11_impl --hidden-import uvicorn.lifespan.on "$root\launcher.py"
if ($LASTEXITCODE -ne 0) { throw 'Portable packaging failed' }
Copy-Item -LiteralPath "$root\docs\PORTABLE-README.txt" -Destination "$stage\dist\RecycleGuard\README.txt"
python "$root\scripts\third-party-notices.py"
Copy-Item -LiteralPath "$root\docs\THIRD_PARTY_NOTICES.txt" -Destination "$stage\dist\RecycleGuard\THIRD_PARTY_NOTICES.txt"
New-Item -ItemType Directory -Force -Path "$root\dist" | Out-Null
Compress-Archive -LiteralPath "$stage\dist\RecycleGuard" -DestinationPath "$root\dist\RecycleGuard-Windows.zip" -Force
Set-Content -LiteralPath "$root\artifacts\portable-build-location.txt" -Value "$stage\dist\RecycleGuard"
Get-FileHash -LiteralPath "$root\dist\RecycleGuard-Windows.zip" -Algorithm SHA256 | Format-List
