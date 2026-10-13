#!/usr/bin/env bash
set -euo pipefail

artifact_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$artifact_root"

python tests/test_pilot.py
python tests/test_controlled.py
python reviewer_evidence/bootstrap_review_evidence/bootstrap_verify.py

echo "Core artifact verification completed successfully."
