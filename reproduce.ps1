param(
    [string]$Python = (Join-Path $PSScriptRoot ".venv\Scripts\python.exe")
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONHASHSEED = "0"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python environment not found at $Python. Run the setup commands in README.md first."
}

$outputRoot = Join-Path $PSScriptRoot "_reproduced"
$tableRoot = Join-Path $outputRoot "tables"
$figureRoot = Join-Path $PSScriptRoot "results\figures"
New-Item -ItemType Directory -Path $tableRoot -Force | Out-Null

$pytestArgs = @("-q", "tests")
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot ".git"))) {
    $pytestArgs += @(
        "--deselect=tests/test_pre_registration.py::TestTheGateRecord::test_every_cited_commit_landed_the_record_it_is_cited_for",
        "--deselect=tests/test_pre_registration.py::TestSealGuards::test_the_confirmatory_directory_was_readme_only_at_the_sealed_commit",
        "--deselect=tests/test_pre_registration.py::TestSealGuards::test_the_0043_number_resolves_and_is_cited_where_the_work_landed"
    )
}

$savedPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $Python -m pytest @pytestArgs 2>&1 | Tee-Object -FilePath (Join-Path $outputRoot "pytest.log")
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $savedPreference
if ($exitCode -ne 0) { exit $exitCode }

$ErrorActionPreference = "Continue"
& $Python -m analysis.report --run-mode confirmatory --out-dir $tableRoot 2>&1 |
    Tee-Object -FilePath (Join-Path $outputRoot "analysis.log")
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $savedPreference
if ($exitCode -ne 0) { exit $exitCode }

if (Test-Path -LiteralPath $figureRoot) {
    Get-ChildItem -LiteralPath $figureRoot -Force |
        Where-Object { $_.Name -ne ".gitkeep" } |
        Remove-Item -Recurse -Force
} else {
    New-Item -ItemType Directory -Path $figureRoot -Force | Out-Null
}

$figureScripts = @(
    "fig_authority_surface.py",
    "fig_breach_by_family.py",
    "figL23_latency.py",
    "fig1_state_board.py"
)
foreach ($figureScript in $figureScripts) {
    $ErrorActionPreference = "Continue"
    & $Python -X utf8 (Join-Path "tools\figures" $figureScript) 2>&1 |
        Tee-Object -FilePath (Join-Path $outputRoot ("figure-" + $figureScript + ".log"))
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $savedPreference
    if ($exitCode -ne 0) { exit $exitCode }
}

$ErrorActionPreference = "Continue"
& $Python -X utf8 tools\figures\acceptance_check.py 2>&1 |
    Tee-Object -FilePath (Join-Path $outputRoot "figure-acceptance.log")
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $savedPreference
if ($exitCode -ne 0) { exit $exitCode }

Write-Output "Reproduction completed. Logs are in _reproduced; figures are in results/figures."
