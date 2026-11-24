"""Exact distance-to-goal heuristics (backward BFS), cached per (map, goal)."""
from __future__ import annotations

import heapq
import math
from collections import deque
from typing import Dict, List, Tuple

from .grid import Cell, Grid

INF = 10**9


def bfs_distances(grid: Grid, goal: Cell) -> List[int]:
    """Unit-cost 4-connected distance from every cell id to ``goal`` (INF if unreachable)."""
    dist = [INF] * (grid.height * grid.width)
    g = grid.to_id(goal)
    if not grid.free[g]:
        raise ValueError(f"goal {goal} is blocked")
    dist[g] = 0
    q = deque([g])
    nbrs = grid.neighbours
    while q:
        v = q.popleft()
        d = dist[v] + 1
        for u in nbrs[v]:
            if dist[u] == INF:
                dist[u] = d
                q.append(u)
    return dist


class HeuristicCache:
    """Caches BFS distance tables keyed by (map name, goal cell)."""

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, Cell], List[int]] = {}

    def get(self, grid: Grid, goal: Cell) -> List[int]:
        key = (grid.name, goal)
        h = self._cache.get(key)
        if h is None:
            h = bfs_distances(grid, goal)
            self._cache[key] = h
        return h

    def __len__(self) -> int:
        return len(self._cache)


_DEFAULT = HeuristicCache()


def get_heuristic(grid: Grid, goal: Cell) -> List[int]:
    return _DEFAULT.get(grid, goal)


def octile_distance(grid: Grid, start: Cell, goal: Cell) -> float:
    """8-connected shortest path (diagonal cost sqrt(2), no corner cutting).

    This is the metric Moving AI uses for the ``optimal_length`` column of the .scen files.
    Used only to sanity-check the parsers; the planners are 4-connected.
    """
    s, g = grid.to_id(start), grid.to_id(goal)
    dist = {s: 0.0}
    pq = [(0.0, s)]
    W, H = grid.width, grid.height
    while pq:
        d, v = heapq.heappop(pq)
        if v == g:
            return d
        if d > dist[v]:
            continue
        r, c = divmod(v, W)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if not (0 <= rr < H and 0 <= cc < W and grid.passable[rr][cc]):
                    continue
                if dr and dc and not (grid.passable[r][cc] and grid.passable[rr][c]):
                    continue  # no corner cutting
                nd = d + (math.sqrt(2) if dr and dc else 1.0)
                u = rr * W + cc
                if nd < dist.get(u, math.inf) - 1e-12:
                    dist[u] = nd
                    heapq.heappush(pq, (nd, u))
    return math.inf
