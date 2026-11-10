param([Parameter(Mandatory=$true)][string]$UnityEditor)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (!(Test-Path -LiteralPath $UnityEditor)) { throw 'Pass the path to a licensed Unity 6 LTS Editor executable.' }
# Unity also needs a reasonably short project path on Windows; copy this project to C:\src if necessary.
& $UnityEditor -batchmode -quit -projectPath "$root\Unity" -executeMethod BuildProject.BuildWindows -logFile "$root\unity-build.log"
if ($LASTEXITCODE -ne 0) { throw "Unity build failed. Read $root\unity-build.log" }
