$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
New-Item -ItemType Directory -Force -Path (Join-Path $root 'build') | Out-Null
$stage = Join-Path $env:TEMP ('recycleguard-compile-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item -LiteralPath "$root\Unity\Assets\Scripts\Core\Simulation.cs" -Destination "$stage\Simulation.cs"
Copy-Item -LiteralPath "$root\Unity\Assets\Scripts\Core\ObservationTimeline.cs" -Destination "$stage\ObservationTimeline.cs"
Copy-Item -LiteralPath "$root\headless\Program.cs" -Destination "$stage\Program.cs"
Push-Location -LiteralPath $stage
try {
    & $compiler /nologo /optimize+ /target:exe /r:System.Web.Extensions.dll /out:RecycleGuard.Core.exe Simulation.cs ObservationTimeline.cs Program.cs
    if ($LASTEXITCODE -ne 0) { throw 'C# compilation failed' }
    Copy-Item -LiteralPath "$stage\RecycleGuard.Core.exe" -Destination "$root\build\RecycleGuard.Core.exe"
} finally { Pop-Location }
# Keep compiler staging files for diagnostics; never delete computed paths recursively.
Write-Host 'Built shared C# simulation host.'
