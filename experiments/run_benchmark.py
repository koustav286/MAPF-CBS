"""Step 7: benchmark CBS and prioritized planning on Moving AI maps.

For each map, k = 2, 4, 6, ... agents (the first k rows of each random scenario file).
An algorithm keeps running on a map until its success rate at some k drops below 10%
(the ``--stop-below`` threshold); the sweep for a map ends when both algorithms have stopped.
Every returned solution is checked by the independent validator before it counts as a
success, and validated solutions are written to results/solutions/ as JSON.

Example:
    python experiments/run_benchmark.py                      # full run (defaults below)
    python experiments/run_benchmark.py --pilot              # scen 1 only, to time the run
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.util import ROOT, machine_info, parse_int_list, write_csv  # noqa: E402

COLUMNS = ["map", "scen", "k", "algorithm", "success", "status", "runtime_s", "soc", "makespan",
           "hl_expanded", "ll_searches", "timeout_s", "fail_reason"]
ALGORITHMS = ("cbs", "pp")
SEED = 2026

_GRIDS: Dict[str, object] = {}


def solve_one(data_dir: str, sol_dir: str, map_name: str, scen: int, k: int, alg: str,
              time_limit: float) -> dict:
    """Worker: solve one instance, validate, save the solution, return a CSV row."""
    from mapf.cbs import cbs
    from mapf.io import load_instance
    from mapf.prioritized import prioritized_planning
    from mapf.validator import find_errors

    random.seed(SEED)
    grid, starts, goals = load_instance(data_dir, map_name, scen, k)
    if map_name in _GRIDS:  # reuse the grid object so the heuristic cache is shared
        grid = _GRIDS[map_name]
    else:
        _GRIDS[map_name] = grid
    solver = cbs if alg == "cbs" else prioritized_planning
    res = solver(grid, starts, goals, time_limit=time_limit)
    row = {"map": map_name, "scen": scen, "k": k, "algorithm": alg, "status": res.status,
           "runtime_s": f"{res.runtime_s:.4f}", "hl_expanded": res.hl_expanded,
           "ll_searches": res.ll_searches, "timeout_s": time_limit, "soc": "", "makespan": "",
           "success": 0, "fail_reason": res.extra.get("reason", "") if not res.success else ""}
    if res.success:
        errs = find_errors(grid.passable, starts, goals, res.paths, forbid_following=True)
        if errs:
            row["status"] = "invalid"
            row["fail_reason"] = "validator: " + errs[0]
            print(f"!!! INVALID SOLUTION {map_name} scen{scen} k{k} {alg}: {errs[0]}", file=sys.stderr)
            return row
        row.update(success=1, soc=res.soc, makespan=res.makespan)
        os.makedirs(sol_dir, exist_ok=True)
        with open(os.path.join(sol_dir, f"{map_name}_{scen}_{k}_{alg}.json"), "w") as f:
            json.dump({"map": map_name, "scen": scen, "k": k, "algorithm": alg, "soc": res.soc,
                       "makespan": res.makespan, "paths": [[list(c) for c in p] for p in res.paths]}, f)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--maps", default="empty-32-32,random-32-32-10,room-32-32-4")
    ap.add_argument("--scens", default="1-10")
    ap.add_argument("--k-step", type=int, default=2)
    ap.add_argument("--k-max", type=int, default=200)
    ap.add_argument("--time-limit", type=float, default=60.0)
    ap.add_argument("--stop-below", type=float, default=0.10)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "benchmark.csv"))
    ap.add_argument("--solutions", default=os.path.join(ROOT, "results", "solutions"))
    ap.add_argument("--pilot", action="store_true", help="scenario 1 only, writes results/pilot.csv")
    args = ap.parse_args()

    maps = args.maps.split(",")
    scens = [1] if args.pilot else parse_int_list(args.scens)
    out = os.path.join(ROOT, "results", "pilot.csv") if args.pilot else args.out
    if args.pilot:
        args.stop_below = 1.0 / len(scens) - 1e-9  # stop an algorithm at its first failure

    header = machine_info()
    header.update(seed=str(SEED), time_limit_s=str(args.time_limit), workers=str(args.workers),
                  conflict_model="vertex+swap+following forbidden",
                  stop_rule=f"an algorithm stops on a map once its success rate at k is < {args.stop_below:.2f}",
                  maps=args.maps, scens=",".join(map(str, scens)))

    rows: List[dict] = []
    t_start = time.time()
    # per-map sweep state
    state = {m: {"k": args.k_step, "active": set(ALGORITHMS)} for m in maps}
    pending: Dict[object, Tuple[str, int]] = {}  # future -> (map, k)
    level_rows: Dict[Tuple[str, int], List[dict]] = {}
    level_left: Dict[Tuple[str, int], int] = {}

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        def submit_level(m: str) -> None:
            st = state[m]
            k = st["k"]
            if not st["active"] or k > args.k_max:
                st["active"] = set()
                return
            key = (m, k)
            level_rows[key] = []
            level_left[key] = 0
            for alg in sorted(st["active"]):
                for s in scens:
                    fut = ex.submit(solve_one, args.data_dir, args.solutions, m, s, k, alg, args.time_limit)
                    pending[fut] = key
                    level_left[key] += 1

        for m in maps:
            submit_level(m)
        while pending:
            done, _ = wait(list(pending), return_when=FIRST_COMPLETED)
            for fut in done:
                key = pending.pop(fut)
                row = fut.result()
                rows.append(row)
                level_rows[key].append(row)
                level_left[key] -= 1
                if level_left[key] == 0:
                    m, k = key
                    msg = []
                    for alg in sorted(state[m]["active"]):
                        rs = [r for r in level_rows[key] if r["algorithm"] == alg]
                        rate = sum(r["success"] for r in rs) / len(rs)
                        msg.append(f"{alg}={rate:.0%}")
                        if rate < args.stop_below:
                            state[m]["active"].discard(alg)
                    print(f"[{time.time() - t_start:7.0f}s] {m:16s} k={k:3d}  " + "  ".join(msg), flush=True)
                    state[m]["k"] += args.k_step
                    submit_level(m)
                    # write partial results so a crash loses little
                    write_csv(out, rows, COLUMNS, header)

    header["total_wall_s"] = f"{time.time() - t_start:.0f}"
    rows.sort(key=lambda r: (r["map"], int(r["k"]), int(r["scen"]), r["algorithm"]))
    write_csv(out, rows, COLUMNS, header)
    n_invalid = sum(r["status"] == "invalid" for r in rows)
    print(f"done: {len(rows)} runs in {time.time() - t_start:.0f}s -> {out}  (invalid: {n_invalid})")
    return 1 if n_invalid else 0


if __name__ == "__main__":
    sys.exit(main())
