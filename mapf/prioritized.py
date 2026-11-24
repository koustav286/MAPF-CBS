"""Prioritized planning (PP) baseline.

Agents are planned one at a time in scenario order (agent 0 has the highest priority) with
space-time A*, against a reservation table built from the paths of all higher-priority agents.
A finished agent reserves its goal forever. If any agent has no path the instance fails; there
are no restarts or priority changes, so the comparison with CBS uses plain PP.
"""
from __future__ import annotations

import time
from typing import List, Sequence

from .astar import SearchTimeout, space_time_astar
from .constraints import ConstraintTable
from .grid import Cell, Grid
from .heuristics import get_heuristic
from .result import SolveResult
from .validator import makespan, sum_of_costs


def reserve_path(table: ConstraintTable, path: Sequence[Cell], forbid_following: bool = True) -> None:
    """Add the constraints a lower-priority agent must respect to avoid ``path``.

    Vertex conflicts: forbid (path[t], t). Following conflicts (either direction): forbid
    (path[t], t-1) and (path[t], t+1); this also rules out swaps. Without the following rule,
    swaps are forbidden explicitly with edge constraints. The goal is blocked forever from the
    arrival time (minus one under the following rule).
    """
    T = len(path) - 1
    for t, c in enumerate(path):
        table.add_vertex(c, t)
        if forbid_following:
            table.add_vertex(c, t - 1)
            if t < T:
                table.add_vertex(c, t + 1)
        elif t < T and path[t + 1] != c:
            table.add_edge(path[t + 1], c, t + 1)  # no swap along this edge
    table.add_permanent(path[-1], T - 1 if forbid_following else T)


def prioritized_planning(grid: Grid, starts: Sequence[Cell], goals: Sequence[Cell],
                         time_limit: float = 60.0, forbid_following: bool = True) -> SolveResult:
    t0 = time.monotonic()
    deadline = t0 + time_limit
    table = ConstraintTable(grid)
    paths: List[List[Cell]] = []
    ll = 0
    try:
        for i, (s, g) in enumerate(zip(starts, goals)):
            ll += 1
            path = space_time_astar(grid, s, g, table, get_heuristic(grid, g), deadline)
            if path is None:
                # "start_blocked": a higher-priority agent enters this agent's start cell so early
                # (t <= 1 under the no-following model) that no plan can exist.
                reason = "start_blocked" if table.vertex_blocked(grid.to_id(s), 0) else "no_path"
                return SolveResult("no_solution", runtime_s=time.monotonic() - t0, ll_searches=ll,
                                   extra={"failed_agent": i, "reason": reason})
            paths.append(path)
            reserve_path(table, path, forbid_following)
    except SearchTimeout:
        return SolveResult("timeout", runtime_s=time.monotonic() - t0, ll_searches=ll)
    return SolveResult("solved", paths=paths, soc=sum_of_costs(paths), makespan=makespan(paths),
                       runtime_s=time.monotonic() - t0, hl_expanded=0, ll_searches=ll)
