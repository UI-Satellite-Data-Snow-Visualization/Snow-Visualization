param(
    [string]$Manifest = "$PSScriptRoot\fall-2026-import.json",
    [switch]$Apply,
    [switch]$UpdateExisting,
    [switch]$Offline
)
$ErrorActionPreference = 'Stop'
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $bundledPython) { $runner = $bundledPython }
elseif ($pythonCommand) { $runner = $pythonCommand.Source }
else { throw 'Python 3.10 or newer is required.' }
$importArguments = @((Join-Path $PSScriptRoot 'import_schedule.py'), $Manifest)
if ($Apply) { $importArguments += '--apply' }
if ($UpdateExisting) { $importArguments += '--update-existing' }
if ($Offline) { $importArguments += '--offline' }
& $runner @importArguments
if ($LASTEXITCODE -ne 0) { throw 'Importer stopped. Read the message above; do not retry writes without a preview.' }
