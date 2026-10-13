param(
    [string]$ArchivePath = 'C:\Users\ossoc\Downloads\OneDrive_1_10-13-2026.zip'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$collection = [IO.Path]::GetFullPath((Join-Path $repoRoot 'db/validation/woodruff'))
if (-not $collection.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar)) {
    throw 'Collection must stay inside the repository.'
}
$entries = @(
    @{ Source = $ArchivePath; Relative = 'source/OneDrive_1_10-13-2026.zip' },
    @{ Source = (Join-Path $repoRoot 'Admin_And_Docs/Planning/woodruff-validation-2026-10-13.md'); Relative = 'reports/woodruff-validation-2026-10-13.md' },
    @{ Source = (Join-Path $repoRoot 'Admin_And_Docs/Planning/woodruff-validation-2026-10-13-results.json'); Relative = 'reports/woodruff-validation-2026-10-13-results.json' },
    @{ Source = (Join-Path $repoRoot 'api/output/woodruff_validation/pc1_covariance.tif'); Relative = 'outputs/pc1_covariance.tif' },
    @{ Source = (Join-Path $repoRoot 'api/output/woodruff_validation/pc1_correlation.tif'); Relative = 'outputs/pc1_correlation.tif' },
    @{ Source = (Join-Path $repoRoot 'api/output/woodruff_validation/results.json'); Relative = 'outputs/results.json' },
    @{ Source = (Join-Path $repoRoot 'api/output/woodruff_validation/run-log.txt'); Relative = 'outputs/run-log.txt' }
)
# Verify all inputs before copying anything. Retain originals and reject conflicts.
foreach ($entry in $entries) {
    if (-not (Test-Path -LiteralPath $entry.Source -PathType Leaf)) {
        throw "Missing input: $($entry.Source)"
    }
    $entry.Hash = (Get-FileHash -LiteralPath $entry.Source -Algorithm SHA256).Hash.ToLowerInvariant()
    $entry.Destination = Join-Path $collection $entry.Relative
    if (Test-Path -LiteralPath $entry.Destination) {
        $existingHash = (Get-FileHash -LiteralPath $entry.Destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($existingHash -ne $entry.Hash) {
            throw "Existing collection file differs; preserve and review it: $($entry.Destination)"
        }
    }
}
$manifest = @()
foreach ($entry in $entries) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $entry.Destination) -Force | Out-Null
    if (-not (Test-Path -LiteralPath $entry.Destination)) {
        Copy-Item -LiteralPath $entry.Source -Destination $entry.Destination
    }
    $copiedHash = (Get-FileHash -LiteralPath $entry.Destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($copiedHash -ne $entry.Hash) { throw "Copy verification failed: $($entry.Relative)" }
    $manifest += [ordered]@{
        path = $entry.Relative
        bytes = (Get-Item -LiteralPath $entry.Destination).Length
        sha256 = $copiedHash
    }
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $collection 'manifest.json') -Encoding utf8
@'
# Woodruff validation collection

All seven collected files were verified with SHA256; see manifest.json.
Original files remain unchanged. This directory is excluded from Git.

- source/: original author-supplied ZIP, including FDL/LDS rasters, boundary and metadata.
- reports/: validation report and detailed measured results.
- outputs/: both generated PC1 GeoTIFFs, results and run log.

The archive is kept intact; extraction is unnecessary for the validation job.
Code remains under api/, because db/ contains stored data only.
Canonical report: ../../../Admin_And_Docs/Planning/woodruff-validation-2026-10-13.md
Validation job: ../../../api/jobs/validate_woodruff.py
Dependencies: ../../../api/requirements.txt and ../../../api/requirements-validation.txt
Collection script: ../../../api/jobs/Collect-WoodruffValidation.ps1

Reproduce from api/ with the configured Python environment:
python -m jobs.validate_woodruff --archive ../db/validation/woodruff/source/OneDrive_1_10-13-2026.zip --out ../db/validation/woodruff/recomputed

Results verify PCA mathematics on author FDL inputs. They do not verify team FDL
dates or agreement with an author PC1 raster; that raster was not supplied.
'@ | Set-Content -LiteralPath (Join-Path $collection 'README.md') -Encoding utf8
Write-Output "Collected and hash-verified $($manifest.Count) files in $collection"
