# Repository-side activation checks. Does not print secret values.
# Run from Mercury_Enterprise_v16/:
#   powershell -File scripts/verify_activation.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
python scripts/verify_activation.py @args
exit $LASTEXITCODE
