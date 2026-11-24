"""Step 10: Monte Carlo ADG execution of the saved benchmark solutions under random delays.

Uses every (map, scen, k) where both CBS and PP succeeded in results/benchmark.csv, loads the
two solutions from results/solutions/, re-validates them, builds their ADGs (checked acyclic),
and simulates R trials per delay probability p and delay model. Every trace must pass the
execution checker before its row is written.

Seed of each trial = first 8 bytes of sha256("map|scen|k|algorithm|p|trial"), recorded in the
CSV, so the per-step and burst models see the same seed for the same trial.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.util import ROOT, machine_info, read_csv, read_header, write_csv  # noqa: E402

COLUMNS = ["map", "scen", "k", "algorithm", "p", "model", "trial", "seed", "planned_soc", "exec_soc",
           "exec_soc_p0", "degradation", "exec_makespan", "num_actions", "type2_edges", "type2_density",
           "coupled_agents", "plan_hash"]
P_LEVELS = (0.0, 0.05, 0.1, 0.2, 0.3)


def trial_seed(m: str, scen: int, k: int, alg: str, p: float, trial: int) -> int:
    h = hashlib.sha256(f"{m}|{scen}|{k}|{alg}|{p}|{trial}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def run_solution(sol_path: str, data_dir: str, models: List[str], p_levels: List[float], trials: int,
                 burst_len: int) -> List[dict]:
    from mapf.adg import build_adg, coupling_metrics, is_acyclic
    from mapf.execution import check_trace, simulate
    from mapf.io import load_instance
    from mapf.validator import find_errors, sum_of_costs

    with open(sol_path) as f:
        sol = json.load(f)
    m, scen, k, alg = sol["map"], sol["scen"], sol["k"], sol["algorithm"]
    paths = [[tuple(c) for c in p] for p in sol["paths"]]
    grid, starts, goals = load_instance(data_dir, m, scen, k)
    errs = find_errors(grid.passable, starts, goals, paths, forbid_following=True)
    if errs:
        raise RuntimeError(f"{sol_path}: saved solution fails validation: {errs[0]}")
    adg = build_adg(paths)
    if not is_acyclic(adg):
        raise RuntimeError(f"{sol_path}: ADG has a cycle")
    met = coupling_metrics(adg)
    planned = sum_of_costs(paths)
    plan_hash = hashlib.sha1(json.dumps(sol["paths"]).encode()).hexdigest()[:12]
    base = simulate(adg, starts, p=0.0)
    if check_trace(base.trace):
        raise RuntimeError(f"{sol_path}: p=0 trace fails the execution checker")
    if base.exec_soc > planned:
        raise RuntimeError(f"{sol_path}: p=0 executed SOC {base.exec_soc} > planned {planned}")
    p0 = base.exec_soc
    rows = []
    for model in models:
        for p in p_levels:
            for trial in range(trials):
                seed = trial_seed(m, scen, k, alg, p, trial)
                if p == 0:
                    r = base
                else:
                    r = simulate(adg, starts, p=p, model=model, rng=random.Random(seed), burst_len=burst_len)
                    errs = check_trace(r.trace)
                    if errs:
                        raise RuntimeError(f"{sol_path} p={p} {model} trial {trial}: {errs[0]}")
                rows.append({
                    "map": m, "scen": scen, "k": k, "algorithm": alg, "p": p, "model": model,
                    "trial": trial, "seed": seed, "planned_soc": planned, "exec_soc": r.exec_soc,
                    "exec_soc_p0": p0, "degradation": f"{(r.exec_soc / p0 - 1) if p0 else 0.0:.6f}",
                    "exec_makespan": r.exec_makespan, "num_actions": met["num_actions"],
                    "type2_edges": met["type2_edges"], "type2_density": f"{met['type2_density']:.6f}",
                    "coupled_agents": met["coupled_agents"], "plan_hash": plan_hash,
                })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", default=os.path.join(ROOT, "results", "benchmark.csv"))
    ap.add_argument("--solutions", default=os.path.join(ROOT, "results", "solutions"))
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "delays.csv"))
    ap.add_argument("--models", default="per_step,burst")
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--burst-len", type=int, default=5)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    bench = read_csv(args.benchmark)
    solved = {}
    for r in bench:
        if r["success"] == "1":
            solved.setdefault((r["map"], int(r["scen"]), int(r["k"])), set()).add(r["algorithm"])
    pairs = sorted(key for key, algs in solved.items() if {"cbs", "pp"} <= algs)
    jobs = []
    for (m, s, k) in pairs:
        for alg in ("cbs", "pp"):
            fn = os.path.join(args.solutions, f"{m}_{s}_{k}_{alg}.json")
            if not os.path.exists(fn):
                print(f"missing solution {fn}; re-run experiments/run_benchmark.py", file=sys.stderr)
                return 1
            jobs.append(fn)
    models = args.models.split(",")
    print(f"{len(pairs)} paired instances, {len(jobs)} solutions, models={models}, R={args.trials}")

    header = machine_info()
    bh = read_header(args.benchmark)
    header.update(benchmark_git_commit=bh.get("git_commit", "?"), trials=str(args.trials),
                  p_levels=",".join(map(str, P_LEVELS)), models=",".join(models), burst_len=str(args.burst_len),
                  seed_rule="sha256('map|scen|k|algorithm|p|trial')[:8]",
                  paired_instances=str(len(pairs)))
    t0 = time.time()
    rows: List[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_solution, fn, args.data_dir, models, list(P_LEVELS), args.trials, args.burst_len)
                for fn in jobs]
        for n, fut in enumerate(as_completed(futs), 1):
            rows.extend(fut.result())
            if n % 50 == 0 or n == len(futs):
                print(f"[{time.time() - t0:6.0f}s] {n}/{len(futs)} solutions", flush=True)
    header["total_wall_s"] = f"{time.time() - t0:.0f}"
    order = {m: i for i, m in enumerate(models)}
    rows.sort(key=lambda r: (r["map"], r["k"], r["scen"], r["algorithm"], order[r["model"]], r["p"], r["trial"]))
    write_csv(args.out, rows, COLUMNS, header)
    print(f"wrote {len(rows)} rows to {args.out} in {time.time() - t0:.0f}s (all traces passed the checker)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
