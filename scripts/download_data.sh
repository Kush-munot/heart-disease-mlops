#!/usr/bin/env bash
# Fetch the raw UCI Cleveland heart disease file and build the cleaned CSV.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m heart.data "$@"
