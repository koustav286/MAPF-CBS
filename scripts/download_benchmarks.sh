#!/usr/bin/env bash
# Download Moving AI MAPF maps and random scenarios into data/ (wrapper around the Python script).
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/download_benchmarks.py --data-dir data
