"""Low-level space-time A* for one agent.

State: (cell, t). Actions: move to a 4-neighbour or wait, each costing 1.
The agent may only *finish* at its goal at a time later than every vertex constraint on the
goal; after finishing it stays there forever.

Two details keep the search finite and fast:
* Horizon cap: no state with t > |free cells| + (latest constraint time) is generated.
* Once t exceeds the latest constraint time nothing is time-dependent any more, so states
  (v, t) with t > max_t are deduplicated on v alone. This is exact: the earliest such state
  is expanded first (consistent heuristic), and every later one has the same successors.
"""
from __future__ import annotations

import heapq
import time
from typing import List, Optional

from .constraints import ConstraintTable
from .grid import Cell, Grid
from .heuristics import INF, get_heuristic


class SearchTimeout(Exception):
    """Raised when the wall-clock deadline passes during a search."""


def space_time_astar(
    grid: Grid,
    start: Cell,
    goal: Cell,
    constraints: Optional[ConstraintTable] = None,
    heuristic: Optional[List[int]] = None,
    deadline: Optional[float] = None,
) -> Optional[List[Cell]]:
    """Shortest constrained path from ``start`` (at t=0) to ``goal``.

    Returns the path as a list of (row, col) cells indexed by time, ending at the first time
    the agent reaches the goal for good (no trailing waits), or None if no path exists.
    Raises SearchTimeout if ``deadline`` (a time.monotonic() value) passes.
    """
    ct = constraints if constraints is not None else ConstraintTable(grid)
    h = heuristic if heuristic is not None else get_heuristic(grid, goal)
    s, g = grid.to_id(start), grid.to_id(goal)
    if not grid.free[s] or h[s] >= INF:
        return None
    ef = ct.earliest_finish(g)
    if ef is None or ct.vertex_blocked(s, 0):
        return None

    max_t = ct.max_t
    horizon = grid.num_free + max_t
    nbrs = grid.neighbours
    blocked = ct.blocked

    # node storage for path reconstruction
    node_v: List[int] = [s]
    node_t: List[int] = [0]
    node_parent: List[int] = [-1]
    open_heap = [(h[s], h[s], 0)]  # (f, h, node index); node index doubles as FIFO tiebreak
    closed = set()
    pops = 0
    while open_heap:
        _, _, idx = heapq.heappop(open_heap)
        v, t = node_v[idx], node_t[idx]
        key = (v, t) if t <= max_t else (v, -1)
        if key in closed:
            continue
        closed.add(key)
        if v == g and t >= ef:
            path = []
            while idx >= 0:
                path.append(grid.to_cell(node_v[idx]))
                idx = node_parent[idx]
            path.reverse()
            return path
        pops += 1
        if deadline is not None and (pops & 1023) == 0 and time.monotonic() > deadline:
            raise SearchTimeout()
        nt = t + 1
        if nt > horizon:
            continue
        for u in nbrs[v] + (v,):
            if blocked(v, u, nt):
                continue
            nkey = (u, nt) if nt <= max_t else (u, -1)
            if nkey in closed:
                continue
            hu = h[u]
            if hu >= INF:
                continue
            node_v.append(u)
            node_t.append(nt)
            node_parent.append(idx)
            heapq.heappush(open_heap, (nt + hu, hu, len(node_v) - 1))
    return None
