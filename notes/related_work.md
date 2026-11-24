# Related work

The first pass (2026-11-24) read the five PDFs in the project folder. The second pass
(2026-11-25) added the NSF-hosted study named in the project brief and three more papers on
ADG execution and delays, found by web search.

## What is known

1. **CBS** (Sharon, Stern, Felner, Sturtevant 2015, AIJ 219): an optimal two-level solver with
   a high-level search over a constraint tree and a single-agent low level. The paper also
   introduces Meta-Agent CBS, which merges agents that conflict more than B times. Its
   experiments (8×8 and 32×32 grids, Dragon Age maps, 5-minute limit) show basic CBS beating
   A*-based solvers in corridor-rich maps and struggling in open spaces, where many
   equal-cost conflicts interact. Part A re-implements the basic version without MA-CBS,
   bypass or later enhancements.
2. **Definitions** (Stern et al. 2019, SoCS): a classical MAPF instance must state which
   conflicts are forbidden (vertex, edge, following, cycle, swapping). Forbidding following
   implies forbidding cycles and swaps. The paper also defines sum of costs under
   stay-at-target.
3. **ADG** (Hönig, Kiesel, Tinka, Durham, Ayanian 2019, RA-L 4(2)): a timed plan becomes an
   action precedence graph. Type 1 edges link one robot's actions. Type 2 edges add
   `(i,k) -> (i',k')` for the *first* `k'` with `s_k^i = g_{k'}^{i'}` and `t_k^i <= t_{k'}^{i'}`
   (Algorithm 1, with `break`). This keeps execution safe under finite delays. Rotation cycles
   become ADG cycles.
4. **Robust MAPF** (Atzmon et al. 2020, JAIR 67): k-robust plans tolerate up to k delays per
   agent. A 1-robust plan equals a MAPF-DP plan (Ma, Kumar, Koenig 2017), i.e. one without
   following moves. The paper compares execution policies such as MCP, which preserves the
   per-vertex visiting order much like an ADG, at delay probabilities 0.001–0.1.
5. **Execution monitoring** (Zahrádka et al. 2025, arXiv:2509.10284): the ADG is safe for plans
   without vertex, edge or cycle conflicts, but following conflicts increase execution time, so
   plans must avoid them. Accumulated delays can make an optimal plan lose to a replanned one.
   Expected completion times are propagated through the ADG.
6. **Which MAPF model works best for warehousing?** (Varambally, Li, Koenig 2022, SoCS; NSF PAR
   10350625, the study named in the brief):
   * Setup: ADG execution combined with rolling-horizon replanning (RHCR), lifelong warehouse
     tasks, Gazebo robots with real dynamics. The paper argues that the ADG gives the same
     robustness as industry's single-agent reservation framework.
   * Comparison: models (standard, with rotations, k-robust, continuous-time) and planners
     (bounded-suboptimal ECBS-TA, and PP with random restarts), measured by throughput over
     three runs.
   * Findings: windowing and modelling rotations raise throughput, and k-robustness helps in
     some cases. Continuous-time PP with exact action durations is best.
   * What it does not do: it uses the vertex + edge model (following allowed), never injects
     random delays at controlled rates, and has no SOC-optimal planner. So it **does not
     answer H1**.
7. **Switchable ADG / receding-horizon re-ordering** (Berndt, van Duijkeren, Palmieri, Kleiner,
   Keviczky; arXiv:2312.04190, IEEE T-RO preprint; workshop version ICAPS 2020): every
   inter-robot dependency gets a reverse twin. A MILP over a receding horizon picks the order
   while keeping the graph acyclic. The authors report "up to a 25% overall decrease in
   average route completion times" under large delays, with MILPs solved in under 1 s for up
   to 70 AGVs. k-robust CBS is better for small bounded delays but rarely finds plans for
   k > 2.
8. **Streamlining the ADG** (Dunkel 2024, arXiv:2412.01277, preprint): wait actions add no
   unique dependency and can be dropped, which we already do. "Sparse candidate partitioning"
   builds Type 2 edges in O(n log n) with at most one Type 2 edge per action, similar to our
   per-cell binary search but sparser than Hönig's rule.
9. **Introducing delays** (Kottinger, Geft, Almagor, Salzman, Lahijanian 2024, arXiv:2307.11252):
   once some agents are delayed, deliberately delay others as little as possible so the rest of
   the plan stays safe. This is NP-complete and APX-hard, and is solved by reduction to MAPF on
   a constrained graph (CBS, EECBS, LNS2). The delay model is worst-case, not probabilistic.

## Positioning of Part B (H1, H2)

- After the second pass, no paper read compares **SOC-optimal CBS plans with prioritized
  plans** on degradation under ADG execution with **controlled random delays**.
  * Varambally et al. come closest: ECBS-TA and PP under ADG. But they measure lifelong
    throughput with realistic dynamics, allow following moves and have no optimal planner.
  * Atzmon et al. compare optimal and k-robust plans.
  * Berndt et al. and Zahrádka et al. improve execution, not plans.

  H1 therefore remains an open empirical question. The finding that optimal plans are not
  more fragile complements Varambally et al.'s throughput results.
- H2 (Type 2 density predicts degradation) builds on Zahrádka et al. and Berndt et al., who
  both identify inter-robot dependencies as the channel through which delays spread. Dunkel's
  sparser construction would change the absolute density values, though probably not the
  ranking.
- **Modelling choice:** both planners forbid vertex, swap and following conflicts (and hence
  cycles), as in Ma et al. 2017, Atzmon et al. 2020 (1-robust) and Zahrádka et al. 2025.
  Varambally et al. use the vertex + edge model instead, so a run under that model is a
  natural robustness check (see ROADMAP.md).
