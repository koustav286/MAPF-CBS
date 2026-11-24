#!/usr/bin/env bash
# Full pipeline: download data, test, benchmark, delay study, analysis, headline report.
# Takes roughly 1-2 hours on an 8-worker laptop (see results/benchmark.csv header for timings).
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/download_benchmarks.py
python -m pytest -q
python experiments/run_benchmark.py          # results/benchmark.csv + results/solutions/*.json
python experiments/analyze.py                # results/summary.md + plots
python experiments/run_delays.py             # results/delays.csv
python experiments/analyze_delays.py         # results/delay_summary.md + plots
python experiments/report.py                 # results/report.md
