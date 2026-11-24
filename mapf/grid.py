"""4-connected grid graph.

Cells are addressed externally as (row, col) tuples; internally the solvers use integer ids
``row * width + col`` for speed. Every action (move to a 4-neighbour, or wait) costs 1.
"""
from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

Cell = Tuple[int, int]

MOVES: Tuple[Cell, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))


class Grid:
    def __init__(self, passable: Sequence[Sequence[bool]], name: str = "grid"):
        self.name = name
        self.height = len(passable)
        self.width = len(passable[0]) if self.height else 0
        if any(len(row) != self.width for row in passable):
            raise ValueError("ragged grid")
        self.passable: List[List[bool]] = [list(map(bool, row)) for row in passable]
        n = self.height * self.width
        self.free: List[bool] = [self.passable[i // self.width][i % self.width] for i in range(n)]
        # neighbours[v] = free 4-neighbours of v (excluding v itself)
        self.neighbours: List[Tuple[int, ...]] = []
        for v in range(n):
            r, c = divmod(v, self.width)
            nb = []
            if self.free[v]:
                for dr, dc in MOVES:
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < self.height and 0 <= cc < self.width and self.passable[rr][cc]:
                        nb.append(rr * self.width + cc)
            self.neighbours.append(tuple(nb))
        self.num_free = sum(self.free)

    # --- conversions -------------------------------------------------------------------
    def to_id(self, cell: Cell) -> int:
        return cell[0] * self.width + cell[1]

    def to_cell(self, v: int) -> Cell:
        return divmod(v, self.width)

    # --- queries -----------------------------------------------------------------------
    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.height and 0 <= cell[1] < self.width

    def is_free(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and self.passable[cell[0]][cell[1]]

    def neighbours_rc(self, cell: Cell) -> List[Cell]:
        """Free 4-neighbours of ``cell`` (the wait action is not included)."""
        if not self.is_free(cell):
            return []
        return [self.to_cell(u) for u in self.neighbours[self.to_id(cell)]]

    def is_valid_step(self, a: Cell, b: Cell) -> bool:
        """True if moving a -> b in one timestep is legal (4-neighbour move or wait)."""
        if not (self.is_free(a) and self.is_free(b)):
            return False
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) <= 1

    def free_cells(self) -> Iterable[Cell]:
        for r in range(self.height):
            for c in range(self.width):
                if self.passable[r][c]:
                    yield (r, c)

    @classmethod
    def from_strings(cls, rows: Sequence[str], name: str = "grid") -> "Grid":
        """Build a grid from strings using '.' for free and '@' for blocked (for tests)."""
        return cls([[ch == "." for ch in row] for row in rows], name=name)
