"""Constraints for the low-level search of a single agent.

* vertex constraint ``(cell, t)``: the agent may not be at ``cell`` at time ``t``.
* edge constraint ``(u, v, t)``: the agent may not move ``u -> v`` arriving at time ``t``.
* permanent block ``(cell, t0)``: the agent may not be at ``cell`` at any time ``t >= t0``
  (used by prioritized planning for cells where higher-priority agents rest at their goals).

Cells are (row, col) tuples in the public API and integer ids inside the table.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set, Tuple

from .grid import Cell, Grid


@dataclass(frozen=True)
class VertexConstraint:
    agent: int
    cell: Cell
    t: int


@dataclass(frozen=True)
class EdgeConstraint:
    agent: int
    u: Cell
    v: Cell
    t: int  # arrival time at v


Constraint = object  # VertexConstraint | EdgeConstraint


class ConstraintTable:
    """Fast lookup structure for one agent's constraints."""

    def __init__(self, grid: Grid):
        self.grid = grid
        self.vertex: Dict[int, Set[int]] = {}
        self.edge: Set[Tuple[int, int, int]] = set()
        self.permanent: Dict[int, int] = {}
        self.max_t = 0  # latest time at which any constraint applies

    # --- building ----------------------------------------------------------------------
    def add_vertex(self, cell: Cell, t: int) -> None:
        if t < 0:
            return
        self.vertex.setdefault(self.grid.to_id(cell), set()).add(t)
        self.max_t = max(self.max_t, t)

    def add_edge(self, u: Cell, v: Cell, t: int) -> None:
        if t < 1:
            return
        self.edge.add((self.grid.to_id(u), self.grid.to_id(v), t))
        self.max_t = max(self.max_t, t)

    def add_permanent(self, cell: Cell, t0: int) -> None:
        t0 = max(t0, 0)
        v = self.grid.to_id(cell)
        old = self.permanent.get(v)
        if old is None or t0 < old:
            self.permanent[v] = t0
        self.max_t = max(self.max_t, t0)

    def add(self, c: Constraint) -> None:
        if isinstance(c, VertexConstraint):
            self.add_vertex(c.cell, c.t)
        elif isinstance(c, EdgeConstraint):
            self.add_edge(c.u, c.v, c.t)
        else:
            raise TypeError(c)

    @classmethod
    def from_constraints(cls, grid: Grid, constraints: Iterable[Constraint], agent: Optional[int] = None) -> "ConstraintTable":
        tab = cls(grid)
        for c in constraints:
            if agent is None or c.agent == agent:
                tab.add(c)
        return tab

    # --- queries (integer ids) ---------------------------------------------------------
    def blocked(self, u: int, v: int, t: int) -> bool:
        """True if moving u -> v arriving at time t is forbidden."""
        ts = self.vertex.get(v)
        if ts is not None and t in ts:
            return True
        p = self.permanent.get(v)
        if p is not None and t >= p:
            return True
        return (u, v, t) in self.edge

    def vertex_blocked(self, v: int, t: int) -> bool:
        ts = self.vertex.get(v)
        if ts is not None and t in ts:
            return True
        p = self.permanent.get(v)
        return p is not None and t >= p

    def earliest_finish(self, goal: int) -> Optional[int]:
        """Earliest time the agent may arrive at ``goal`` and stay there forever.

        Returns None if the goal is permanently blocked (the agent can never finish).
        """
        if goal in self.permanent:
            return None
        ts = self.vertex.get(goal)
        return (max(ts) + 1) if ts else 0
