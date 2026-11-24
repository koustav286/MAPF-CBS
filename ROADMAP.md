# Roadmap: what is done, what is weak, what comes next

Last updated 2026-11-25. All results referred to here are in `results/`. The method is in
`README.md` and the literature in `notes/related_work.md`.

## 1. Done

| step | what | where |
|---|---|---|
| 0 | Literature check, two passes: 5 local PDFs plus 4 papers found by web search, including the NSF-hosted Varambally et al. 2022 | `notes/related_work.md` |
| 1 | Moving AI parsers and downloader; sanity test against octile distances | `mapf/io.py`, `scripts/download_benchmarks.py` |
| 2 | 4-connected grid; backward-BFS heuristic cached per (map, goal) | `mapf/grid.py`, `mapf/heuristics.py` |
| 3 | Space-time A* with vertex, edge and permanent constraints | `mapf/astar.py`, `mapf/constraints.py` |
| 4 | Independent validator for vertex, swap and following conflicts | `mapf/validator.py` |
| 5 | Plain prioritized planning (fixed order, no restarts) | `mapf/prioritized.py` |
| 6 | Basic CBS; optimality checked against a brute-force joint search on 4×4 maps | `mapf/cbs.py`, `tests/test_cbs.py` |
| 7 | Benchmark: 3 maps × 10 scenarios × k = 2, 4, …; 1,350 runs, 0 invalid | `experiments/run_benchmark.py`, `results/benchmark.csv` |
| 8 | Benchmark analysis: success, runtime, PP suboptimality | `experiments/analyze.py`, `results/summary.md` |
| 9 | ADG (Hönig et al. Algorithm 1) and coupling metrics; acyclicity checked | `mapf/adg.py` |
| 10 | Delay simulator, execution checker, 160,800 checked executions, H1/H2 statistics | `mapf/execution.py`, `experiments/run_delays.py`, `experiments/analyze_delays.py` |
| 11 | README with generated tables and plots | `README.md`, `scripts/update_readme.py` |
| 12 | CI workflow, reproduction script, fresh-clone check (`REPRODUCED`), headline report | `.github/workflows/ci.yml`, `scripts/`, `results/report.md` |

Headline result: H1 is not supported (optimal CBS plans are not more fragile than PP plans).
H2 is supported (Type 2 density predicts degradation beyond the number of agents). Most of the
slowdown is each robot's own delay.

## 2. Known failures and weak spots of the current work

Each item says how it would show up to a reviewer and what fixes it. The ones marked ★ change
the conclusions most if left alone.

1. ★ **Weak PP baseline.** 348 of plain PP's 359 failures are `start_blocked`: a
   higher-priority robot enters a lower-priority robot's start cell at t ≤ 1, which the
   no-following model cannot repair. This shrinks the paired set and handicaps PP.
   *Fix:* stronger PP variants (§3.1), re-run, and check whether H1 still holds.
2. ★ **Small instances only.** Basic Python CBS solves at least 50% of instances only up to
   k = 16–26, so the delay study covers 268 instances averaging 12 robots. The crowded regime,
   where coupling should matter most, is untested.
   *Fix:* faster optimal or bounded-suboptimal solvers (§3.2, §4).
3. **CBS blows up on some small instances.** For example, it times out at k = 8 even though
   no pair of agents is hard on its own; the cause is many equal-cost conflicts interacting.
   *Fix:* conflict prioritization (cardinal conflicts), bypassing, disjoint splitting,
   symmetry reasoning, and admissible high-level heuristics (§3.2).
4. **Noise on identical plans.** The seed includes the algorithm name (as the spec asked),
   so when CBS and PP return the same plan (98 of 268 pairs) they still get different random
   delays. *Fix:* common random numbers, i.e. delays drawn per (instance, robot, step),
   independent of the algorithm. Analyse the differing-plan subset as the main test.
5. **Statistics could be sharper.** Wilcoxon tests pool all maps and k. *Fix:* a mixed-effects
   or stratified analysis (instance as random effect, map and k as covariates), effect sizes
   with bootstrap confidence intervals, and a power estimate for "no difference".
6. **The "coupling excess" is exploratory.** The reference p/(1−p) is not a strict bound,
   because waits already in a plan can absorb delays. *Fix:* compute the true no-coupling
   reference by simulating each robot alone with the same random draws.
7. **Only one conflict model.** We forbid following moves; Varambally et al. allow them.
   *Fix:* also run the vertex + swap model (planners already support `forbid_following=False`)
   and report how much ADG execution stretches convoys.
8. **Synthetic delay models.** Delays are independent per step or fixed-length bursts.
   *Fix:* heterogeneous robots (some slower), correlated or location-dependent delays,
   continuous-time durations, or delay traces from real robots.
9. **One-shot instances, not lifelong.** Warehouses run continuously (Varambally et al.
   measure throughput). *Fix:* a rolling-horizon / lifelong variant with throughput as the
   metric.
10. **Noisy runtimes.** 8 parallel workers on a laptop CPU with mixed core types. *Fix:* pin
    workers to performance cores, repeat runs, and report variance near the time limit.
11. **Housekeeping.**
    * CI has not run yet; it will on the first push.
    * `results/delays.csv` is 18 MB; consider compressing it.
    * The ADG density follows Hönig's rule; Dunkel's sparser construction would change
      absolute values.

## 3. Next steps inside the current design

### 3.1 Stronger prioritized-planning baselines
1. **Start-cell protection / Revised Prioritized Planning** (Čáp et al. 2015): higher-priority
   robots avoid the start cells of lower-priority robots. This removes `start_blocked`
   failures and is complete on well-formed instances.
2. **PP with random restarts** (as in Varambally et al. 2022): retry with shuffled priority
   orders until solved or out of time.
3. **Priority-Based Search (PBS)** (Ma et al. 2019): search over priority orderings. Stronger
   than PP, usually near-optimal, and it scales far beyond CBS.
4. Re-run Step 7 and Step 10 with these baselines, keeping plain PP as a reference arm.

### 3.2 Making CBS scale (still our own Python implementation)
1. Conflict prioritization with MDDs (cardinal, semi-cardinal and non-cardinal conflicts),
   from ICBS (Boyarski et al. 2015).
2. Bypassing conflicts (Boyarski et al. 2015) and disjoint splitting (Li et al. 2019).
3. Symmetry reasoning for rectangle, corridor and target conflicts (Li et al. 2019–2021);
   this targets exactly the blow-ups we saw.
4. Admissible high-level heuristics such as CG, DG and WDG (Felner et al. 2018; Li et al. 2019),
   i.e. the CBSH2-RTC configuration.
5. Bounded-suboptimal variants, ECBS and EECBS (Barer et al. 2014; Li, Ruml, Koenig 2021), to
   reach hundreds of agents with a known cost bound.
6. A third arm for the delay study: **k-robust CBS** (Atzmon et al. 2020), the optional item in
   the original spec.

### 3.3 Fixes to the experiments
Common random numbers (§2.4), a true no-coupling reference (§2.6), a mixed-effects analysis
(§2.5), the vertex + swap model run (§2.7), and more delay models (§2.8).

## 4. Options beyond pure-Python CBS

Each option is listed with what it gives and what it costs. The project's hard rule ("implement
the algorithms myself, no external MAPF libraries") is respected by options A and B. Option C
needs an explicit decision, because it uses other people's solvers as *comparison baselines*
(clearly labelled, never presented as ours).

**A. Make our own code faster without changing the algorithm**
- *PyPy:* often 3–10× faster for pure-Python search loops; no code changes, though numpy/scipy
  support needs checking.
- *Numba or Cython for the low-level A\*:* A* is where most time goes. This takes moderate
  effort and gives a large speed-up.
- *Rewrite the core (A\*, CBS, PP) in C++ with pybind11, or in Rust with PyO3,* keeping Python
  for experiments and analysis. This usually gives 20–100× and makes us comparable with
  published CBS numbers. It is the most effort, and the code is still our own.

**B. Different algorithm families, implemented ourselves**
- *Search-based, scalable:*
  * PBS (§3.1) and EECBS (§3.2).
  * LaCAM / LaCAM\* (Okumura 2023): very fast, complete, handles thousands of agents; LaCAM\*
    converges towards optimal over time.
  * PIBT (Okumura et al. 2022): a one-step-at-a-time rule; extremely fast, suboptimal.
  * MAPF-LNS / LNS2 (Li et al. 2021–2022): anytime improvement of a feasible solution.
- *Reduction-based optimal solvers:* SAT (Surynek et al.) or branch-and-cut-and-price (BCP,
  Lam & Le Bodic 2022), using a general-purpose SAT/MIP solver, which is not a MAPF library.
  Strong on small, dense instances.
- These give a spectrum of plan types (optimal, near-optimal, greedy), which makes H1 more
  general than "CBS vs PP".

**C. Established implementations as reference baselines (needs your decision)**
- Public C++ code exists for CBSH2-RTC, EECBS, PBS, MAPF-LNS2 (Jiaoyang Li et al.) and
  LaCAM/LaCAM\* (Okumura).
- Running their solvers, then executing their plans through our ADG simulator, would test H1
  and H2 on hundreds of agents within days.
- Their plans use the vertex + edge model, so following moves would need handling, either by
  modifying their code or by reporting the convoy stretch.

**D. Execution-side methods, an alternative research direction**
- Switchable ADG with receding-horizon re-ordering (Berndt et al. 2023), commit-cut replanning
  (Hönig et al. 2019), monitoring with expected completion times (Zahrádka et al. 2025), and
  minimal delay introduction (Kottinger et al. 2024).
- These improve execution of a given plan, and pair naturally with our simulator.

## 5. The research direction this sets up

The delay study gives us a measuring stick. The natural new contribution is a **planner that
knows about execution**, i.e. one that plans for the delays it will face. Concretely:
- a CBS or PBS variant that breaks cost ties by fewer Type 2 dependencies, or minimizes
  expected ADG execution time under a delay model (cf. Ma et al. 2017, Wagner's SL-CBS);
- evaluated with this repository's simulator against plain CBS, PP variants and k-robust CBS.

H2's result (density predicts slowdown beyond crowding) is the evidence that such a planner
has something to optimize.

## 6. Suggested order

1. Stronger PP (RPP plus restarts) and common random numbers, then re-run: this checks whether
   H1 is robust. About 1 day.
2. CBS enhancements (prioritization and bypass first, then symmetry reasoning and WDG): about
   3–5 days.
3. Decide between option A (C++/Rust core) and option C (external baselines) for large-k
   experiments.
4. An execution-aware planner prototype (§5).
