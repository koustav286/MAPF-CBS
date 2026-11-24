"""Independent solution validator (the truth oracle for every counted success).

Deliberately does not import any solver code. Paths are lists of (row, col) indexed by time,
starting at t=0. Shorter paths are padded by repeating their last cell (stay-at-target).

Conflict model (Stern et al. 2019 terminology). Always forbidden:
  * vertex conflict:   pos_i(t) == pos_j(t)
  * swap conflict:     pos_i(t) == pos_j(t+1) and pos_j(t) == pos_i(t+1)
With ``forbid_following=True`` (the model used throughout this project, following
Ma et al. 2017 / Atzmon et al. 2020 / Zahradka et al. 2025):
  * following conflict: pos_i(t+1) == pos_j(t) for i != j
which also excludes cycle (rotation) conflicts.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

Cell = Tuple[int, int]
Path = Sequence[Cell]


class InvalidSolution(Exception):
    pass


def path_cost(path: Path) -> int:
    """Arrival time at the goal, ignoring trailing waits (Stern et al. 2019 SOC convention)."""
    T = len(path) - 1
    while T > 0 and tuple(path[T - 1]) == tuple(path[-1]):
        T -= 1
    return T


def sum_of_costs(paths: Sequence[Path]) -> int:
    return sum(path_cost(p) for p in paths)


def makespan(paths: Sequence[Path]) -> int:
    return max((path_cost(p) for p in paths), default=0)


def _free(passable, c: Cell) -> bool:
    r, col = c
    return 0 <= r < len(passable) and 0 <= col < len(passable[0]) and bool(passable[r][col])


def find_errors(passable, starts: Sequence[Cell], goals: Sequence[Cell], paths: Sequence[Path],
                forbid_following: bool = True, max_errors: int = 20) -> List[str]:
    """Return a list of human-readable problems (empty list = valid solution).

    ``passable`` is a 2-D boolean array (rows x cols), e.g. ``grid.passable``.
    """
    errs: List[str] = []
    k = len(starts)
    if len(goals) != k or len(paths) != k:
        return [f"expected {k} starts/goals/paths, got {len(starts)}/{len(goals)}/{len(paths)}"]
    P = [[tuple(c) for c in p] for p in paths]
    for i, p in enumerate(P):
        if not p:
            errs.append(f"agent {i}: empty path")
            continue
        if p[0] != tuple(starts[i]):
            errs.append(f"agent {i}: starts at {p[0]}, expected {tuple(starts[i])}")
        if p[-1] != tuple(goals[i]):
            errs.append(f"agent {i}: ends at {p[-1]}, expected {tuple(goals[i])}")
        for t, c in enumerate(p):
            if not _free(passable, c):
                errs.append(f"agent {i}: blocked/out-of-bounds cell {c} at t={t}")
        for t in range(len(p) - 1):
            a, b = p[t], p[t + 1]
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) > 1:
                errs.append(f"agent {i}: illegal move {a}->{b} at t={t}")
    if errs:
        return errs[:max_errors]

    T = max(len(p) for p in P) - 1

    def pos(i: int, t: int) -> Cell:
        p = P[i]
        return p[t] if t < len(p) else p[-1]

    for t in range(T + 1):
        seen = {}
        for i in range(k):
            c = pos(i, t)
            if c in seen:
                errs.append(f"vertex conflict: agents {seen[c]} and {i} at {c}, t={t}")
            else:
                seen[c] = i
        if t == T:
            break
        nxt = {}
        for i in range(k):
            nxt[pos(i, t + 1)] = i
        for i in range(k):
            a, b = pos(i, t), pos(i, t + 1)
            if a == b:
                continue
            j = seen.get(b)  # who was at b at time t
            if j is None or j == i:
                continue
            if pos(j, t + 1) == a:
                if i < j:
                    errs.append(f"swap conflict: agents {i} and {j} on {a}<->{b}, t={t}->{t + 1}")
            elif forbid_following:
                errs.append(f"following conflict: agent {i} enters {b} at t={t + 1} which agent {j} left at t={t}")
        if len(errs) >= max_errors:
            break
    return errs[:max_errors]


def validate(passable, starts, goals, paths, forbid_following: bool = True) -> None:
    """Raise InvalidSolution if the joint plan is not a valid MAPF solution."""
    errs = find_errors(passable, starts, goals, paths, forbid_following=forbid_following)
    if errs:
        raise InvalidSolution("; ".join(errs))


def is_valid(passable, starts, goals, paths, forbid_following: bool = True) -> bool:
    return not find_errors(passable, starts, goals, paths, forbid_following=forbid_following, max_errors=1)
