# Related work (Step 0 literature check)

Sources read: the five PDFs in the project folder (full text for Hönig et al. 2019 and the
relevant sections of the others). No web search was run for this check, so the
"NSF-hosted study comparing MAPF models under ADG execution" mentioned in the spec was **not**
checked. It should be read before the README claims novelty for H1.

## What is known

1. **CBS** (Sharon, Stern, Felner, Sturtevant 2015, AIJ 219) is a two-level, optimal MAPF solver:
   a high-level search over constraint trees, with a low-level single-agent search per agent.
   Part A re-implements the basic version, with no bypass, prioritising or disjoint splitting.
2. **Definitions** (Stern et al. 2019, SoCS): a classical MAPF instance must state which
   conflicts are forbidden: vertex, edge, following, cycle and swapping. Forbidding following
   implies forbidding cycle and swapping. The paper also defines sum of costs (SOC) under
   stay-at-target as the time each agent last arrives at its target.
3. **ADG** (Hönig, Kiesel, Tinka, Durham, Ayanian 2019, RA-L 4(2)): turns a timed MAPF plan into
   an action precedence graph. Type 1 edges link consecutive actions of one robot. Type 2 edges
   add `(i,k) -> (i',k')` for the *first* `k'` with `s_k^i = g_{k'}^{i'}` and
   `t_k^i <= t_{k'}^{i'}` (Algorithm 1, with a `break`). Execution enqueues an action only when
   all its Type 2 predecessors are finished, which keeps robots collision-free under arbitrary
   finite delays. Rotation cycles in a plan show up as cycles in the ADG and cannot be executed.
4. **Robust MAPF** (Atzmon, Stern, Felner, Wagner, Barták, Zhou 2020, JAIR 67): *k*-robust plans
   tolerate up to k delays per agent without collisions, at a small cost increase. A 1-robust plan
   equals a MAPF-DP plan (Ma, Kumar, Koenig 2017), meaning no following moves. The paper compares
   execution policies (e.g. MCP, which preserves the per-vertex visiting order, much like an ADG)
   under delay probabilities 0.001–0.1. Using k-robust plans as input reduces the number of
   repairs needed during execution.
5. **Execution monitoring** (Zahrádka et al. 2025, arXiv:2509.10284): the ADG guarantees safe
   execution of any plan without vertex, edge or cycle conflicts, but **following conflicts
   increase execution time**, because a Type 2 edge forces the follower to wait for the leader to
   finish. Zahrádka et al. therefore require plans without following conflicts. They show that
   accumulated delays make an originally optimal plan lose to replanned alternatives in some
   cases, and they propagate expected completion times through the ADG.

## Positioning of Part B (H1, H2)

- None of the papers read compares **SOC-optimal CBS plans against prioritized-planning plans**
  on how much they degrade under ADG execution with random delays. Atzmon et al. compare optimal
  against k-robust plans under repair policies, and Zahrádka et al. study when to replan. H1 is
  therefore framed as an open empirical question on Moving AI benchmarks, with the caveat that
  the NSF-hosted study above was not checked.
- H2 (Type 2 density predicts degradation) builds on Zahrádka et al.'s point that Type 2 edges
  are the channel through which one robot's delay spreads to others.
- **Modelling choice taken from this literature:** both planners forbid vertex, swap and
  following conflicts (and hence cycle conflicts), as in Ma et al. 2017, Atzmon et al. 2020
  (1-robust) and Zahrádka et al. 2025. Under this model, every ADG is acyclic, and execution
  with p = 0 reproduces the planned timing (minus dropped waits). Part A is therefore a
  re-implementation of CBS and PP for the **no-following MAPF variant**, not the plain
  vertex + swap variant.
