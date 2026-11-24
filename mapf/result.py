"""Common result record returned by the MAPF solvers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

Cell = Tuple[int, int]


@dataclass
class SolveResult:
    status: str  # "solved" | "no_solution" | "timeout"
    paths: Optional[List[List[Cell]]] = None
    soc: Optional[int] = None
    makespan: Optional[int] = None
    runtime_s: float = 0.0
    hl_expanded: int = 0
    ll_searches: int = 0
    extra: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == "solved"
