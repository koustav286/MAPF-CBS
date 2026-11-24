"""Compare freshly generated result CSVs with the committed ones.

Deterministic quantities must match exactly on every key present in both files:
  * benchmark.csv: SOC and makespan of every instance solved in both runs
    (runtimes, and therefore which borderline instances finish before the time limit, may differ);
  * delays.csv: every column except nothing time-dependent - the simulation is seeded.

Usage:
    python scripts/check_reproduction.py --fresh-dir /path/to/fresh/results [--committed-dir results]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.util import ROOT, read_csv  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fresh-dir", required=True)
    ap.add_argument("--committed-dir", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()
    bad = 0

    def key(r, cols):
        return tuple(r[c] for c in cols)

    kb = ("map", "scen", "k", "algorithm")
    old = {key(r, kb): r for r in read_csv(os.path.join(args.committed_dir, "benchmark.csv"))}
    new = {key(r, kb): r for r in read_csv(os.path.join(args.fresh_dir, "benchmark.csv"))}
    both = [k for k in new if k in old and old[k]["success"] == "1" and new[k]["success"] == "1"]
    for k in both:
        for c in ("soc", "makespan"):
            if old[k][c] != new[k][c]:
                bad += 1
                print(f"benchmark mismatch {k} {c}: committed {old[k][c]} fresh {new[k][c]}")
    flips = sum(1 for k in new if k in old and old[k]["success"] != new[k]["success"])
    print(f"benchmark: {len(both)} instances solved in both runs compared; "
          f"{flips} success flips (time-limit sensitive, reported only)")

    dn = os.path.join(args.fresh_dir, "delays.csv")
    if os.path.exists(dn):
        kd = ("map", "scen", "k", "algorithm", "p", "model", "trial")
        old_d = {key(r, kd): r for r in read_csv(os.path.join(args.committed_dir, "delays.csv"))}
        n = 0
        for r in read_csv(dn):
            o = old_d.get(key(r, kd))
            if o is None:
                continue
            n += 1
            if o != r:
                bad += 1
                if bad < 20:
                    print(f"delay mismatch {key(r, kd)}: {[c for c in r if r[c] != o.get(c)]}")
        print(f"delays: {n} rows present in both compared")
    print("REPRODUCED" if bad == 0 else f"{bad} MISMATCHES")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
