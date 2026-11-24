"""Download the Moving AI MAPF maps and "random" scenario files used in this project.

Usage:  python scripts/download_benchmarks.py [--data-dir data]

Fetches mapf-map.zip and mapf-scen-random.zip from https://movingai.com/benchmarks/mapf/
and extracts only the three maps and their random-1..25 scenario files into
data/maps/ and data/scens/.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import urllib.request
import zipfile

BASE = "https://movingai.com/benchmarks/mapf/"
MAPS = ["empty-32-32", "random-32-32-10", "room-32-32-4"]
ZIPS = {"mapf-map.zip": "maps", "mapf-scen-random.zip": "scens"}


def wanted(name: str) -> bool:
    base = os.path.basename(name)
    return any(base == f"{m}.map" or base.startswith(f"{m}-random-") for m in MAPS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    args = ap.parse_args()
    for zname, sub in ZIPS.items():
        out = os.path.join(args.data_dir, sub)
        os.makedirs(out, exist_ok=True)
        url = BASE + zname
        print(f"downloading {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "mapf-benchmark-downloader"})
        with urllib.request.urlopen(req, timeout=120) as r:
            blob = r.read()
        n = 0
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            for info in z.infolist():
                if info.is_dir() or not wanted(info.filename):
                    continue
                with open(os.path.join(out, os.path.basename(info.filename)), "wb") as f:
                    f.write(z.read(info))
                n += 1
        print(f"  extracted {n} files to {out}")
        if n == 0:
            print("  ERROR: no matching files found in archive", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
