"""Conflict-Based Search (Sharon, Stern, Felner, Sturtevant 2015), basic version.

High level: best-first search over constraint-tree nodes ordered by
(sum of costs, number of conflicts, insertion order). Each node holds per-agent constraints,
one path per agent, its SOC and its conflict count. Expanding a node splits on its *first*
(earliest) conflict into two children, each adding one constraint to one agent and replanning
only that agent with space-time A*. Children whose agent has no path are dropped.

Conflicts and how they are split (``forbid_following=True`` is the project's model):
  * vertex (i, j, c, t):                 i: not at c at t      |  j: not at c at t
  * following (i enters c at t, j left c at t-1):
                                          i: not at c at t      |  j: not at c at t-1
    (any solution without following conflicts satisfies at least one of the two, so the
    split is sound and CBS stays optimal for this model; it also covers swaps and cycles)
  * swap (only when following is allowed): edge constraints u->v at t / v->u at t.

No enhancements (bypass, prioritizing conflicts, disjoint splitting, heuristics) are used.
"""
from __future__ import annotations

import heapq
import time
from typing import FrozenSet, List, Optional, Sequence, Tuple

from .astar import SearchTimeout, space_time_astar
from .constraints import ConstraintTable
from .grid import Cell, Grid
from .heuristics import get_heuristic
from .result import SolveResult
from .validator import makespan, path_cost, sum_of_costs

# A constraint is ('v', cell, t) or ('e', u, v, t); a conflict is a tuple described in
# detect_conflicts.
AgentConstraints = FrozenSet[tuple]


def detect_conflicts(paths: Sequence[Sequence[Cell]], forbid_following: bool = True):
    """Return (first conflict or None, number of conflicts).

    Conflicts are ordered by time; at equal time, vertex conflicts come first. Formats:
      ('vertex', i, j, cell, t)
      ('following', follower, leader, cell, t)   follower at cell at t, leader there at t-1
      ('swap', i, j, u, v, t)                    i: u->v and j: v->u arriving at t
    """
    k = len(paths)
    T = max(len(p) for p in paths) - 1
    first = None
    count = 0
    prev_occ = None
    prev_pos = None
    for t in range(T + 1):
        cur = [p[t] if t < len(p) else p[-1] for p in paths]
        occ = {}
        for i in range(k):
            c = cur[i]
            j = occ.get(c)
            if j is not None:
                count += 1
                if first is None:
                    first = ("vertex", j, i, c, t)
            else:
                occ[c] = i
        if prev_occ is not None:
            for i in range(k):
                c = cur[i]
                if c == prev_pos[i]:
                    continue
                j = prev_occ.get(c)
                if j is None or j == i or cur[j] == c:  # cur[j] == c is a vertex conflict
                    continue
                if forbid_following:
                    count += 1
                    if first is None:
                        first = ("following", i, j, c, t)
                elif cur[j] == prev_pos[i] and i < j:
                    count += 1
                    if first is None:
                        first = ("swap", i, j, prev_pos[i], c, t)
        prev_occ, prev_pos = occ, cur
    return first, count


def split(conflict) -> List[Tuple[int, tuple]]:
    """The two (agent, constraint) branches for a conflict."""
    kind = conflict[0]
    if kind == "vertex":
        _, i, j, c, t = conflict
        return [(i, ("v", c, t)), (j, ("v", c, t))]
    if kind == "following":
        _, f, l, c, t = conflict
        return [(f, ("v", c, t)), (l, ("v", c, t - 1))]
    if kind == "swap":
        _, i, j, u, v, t = conflict
        return [(i, ("e", u, v, t)), (j, ("e", v, u, t))]
    raise ValueError(conflict)


def _table(grid: Grid, cons: AgentConstraints) -> ConstraintTable:
    tab = ConstraintTable(grid)
    for c in cons:
        if c[0] == "v":
            tab.add_vertex(c[1], c[2])
        else:
            tab.add_edge(c[1], c[2], c[3])
    return tab


def cbs(grid: Grid, starts: Sequence[Cell], goals: Sequence[Cell], time_limit: float = 60.0,
        forbid_following: bool = True) -> SolveResult:
    t0 = time.monotonic()
    deadline = t0 + time_limit
    k = len(starts)
    heur = [get_heuristic(grid, g) for g in goals]
    hl = ll = 0

    def plan(a: int, cons: AgentConstraints) -> Optional[List[Cell]]:
        nonlocal ll
        ll += 1
        return space_time_astar(grid, starts[a], goals[a], _table(grid, cons), heur[a], deadline)

    def done(status, paths=None):
        extra = {}
        res = SolveResult(status, runtime_s=time.monotonic() - t0, hl_expanded=hl, ll_searches=ll, extra=extra)
        if paths is not None:
            res.paths, res.soc, res.makespan = [list(p) for p in paths], sum_of_costs(paths), makespan(paths)
        return res

    try:
        empty: AgentConstraints = frozenset()
        root_paths = []
        for a in range(k):
            p = plan(a, empty)
            if p is None:
                return done("no_solution")
            root_paths.append(p)
        first, nconf = detect_conflicts(root_paths, forbid_following)
        counter = 0
        # heap entry: (soc, n_conflicts, id, constraints tuple, paths, first conflict)
        open_list = [(sum_of_costs(root_paths), nconf, counter, (empty,) * k, root_paths, first)]
        while open_list:
            if time.monotonic() > deadline:
                return done("timeout")
            soc, nconf, _, cons, paths, first = heapq.heappop(open_list)
            hl += 1
            if first is None:
                return done("solved", paths)
            for agent, c in split(first):
                if c in cons[agent]:
                    continue  # cannot happen for a correct path; guard against loops
                new_cons_a = cons[agent] | {c}
                p = plan(agent, new_cons_a)
                if p is None:
                    continue
                new_paths = list(paths)
                new_paths[agent] = p
                new_cons = cons[:agent] + (new_cons_a,) + cons[agent + 1 :]
                f, n = detect_conflicts(new_paths, forbid_following)
                counter += 1
                new_soc = soc - path_cost(paths[agent]) + path_cost(p)
                heapq.heappush(open_list, (new_soc, n, counter, new_cons, new_paths, f))
        return done("no_solution")
    except SearchTimeout:
        return done("timeout")
