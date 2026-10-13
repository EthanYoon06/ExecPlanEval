$ErrorActionPreference = "Stop"
$ArtifactRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ArtifactRoot

python tests/test_pilot.py
python tests/test_controlled.py
python reviewer_evidence/bootstrap_review_evidence/bootstrap_verify.py

Write-Output "Core artifact verification completed successfully."
