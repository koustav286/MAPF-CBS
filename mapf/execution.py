"""Discrete-time ADG execution under random delays, plus an independent execution checker.

Simulator
---------
Time advances in steps T = 0, 1, 2, ... Each move action takes one step: an action started in
step T is complete at time T+1. At the start of step T an agent is *ready* if it has an
unfinished next action whose ADG predecessors (Type 2 sources; the Type 1 predecessor is its
own previous action) are all complete. A ready agent then either executes the action or is
delayed:

* ``per_step`` (primary): frozen for this step with probability p.
* ``burst`` (secondary): with probability p it is frozen for D consecutive steps (this one
  included); when the burst ends it is ready again and draws again.

The executed cost of an agent is the time its last action completes (0 if it has no moves);
executed SOC is the sum over agents.

Deadlock guard: if no agent is ready for ``deadlock_steps`` consecutive steps (while some are
unfinished) a DeadlockError is raised. A correct (acyclic) ADG never deadlocks, so this signals
a bug.

Execution checker
-----------------
``check_trace`` looks only at the recorded positions: every agent moves at most one 4-neighbour
cell per step, no two agents share a cell at the same time, and no two agents swap cells.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .adg import ADG

Cell = Tuple[int, int]


class DeadlockError(RuntimeError):
    pass


@dataclass
class ExecResult:
    arrivals: List[int]
    exec_soc: int
    exec_makespan: int
    steps: int
    trace: Optional[List[Tuple[Cell, ...]]]  # trace[T][i] = position of agent i at time T


def simulate(adg: ADG, starts: Sequence[Cell], p: float = 0.0, model: str = "per_step",
             rng: Optional[random.Random] = None, burst_len: int = 5, record_trace: bool = True,
             deadlock_steps: int = 1000, max_steps: Optional[int] = None) -> ExecResult:
    if model not in ("per_step", "burst"):
        raise ValueError(model)
    if p > 0 and rng is None:
        raise ValueError("rng required when p > 0")
    k = adg.num_agents
    acts = adg.actions
    n = [len(a) for a in acts]
    preds = [[adg.type2_in.get((i, l), ()) for l in range(n[i])] for i in range(k)]
    done = [0] * k  # number of completed actions per agent
    frozen = [0] * k  # remaining burst steps
    pos = [tuple(s) for s in starts]
    arrivals = [0] * k
    trace = [tuple(pos)] if record_trace else None
    unfinished = sum(1 for i in range(k) if n[i] > 0)
    if max_steps is None:
        max_steps = 1000 * (adg.num_actions + 1) + 10 * deadlock_steps
    T = 0
    idle = 0
    while unfinished:
        if T >= max_steps:
            raise RuntimeError(f"simulation exceeded {max_steps} steps")
        moving = []
        any_ready = False
        for i in range(k):
            l = done[i]
            if l >= n[i]:
                continue
            if any(done[j] <= m for (j, m) in preds[i][l]):
                continue  # waiting on another agent
            any_ready = True
            if frozen[i] > 0:
                frozen[i] -= 1
                continue
            if p > 0 and rng.random() < p:
                if model == "burst":
                    frozen[i] = burst_len - 1
                continue
            moving.append(i)
        if not any_ready:
            idle += 1
            if idle >= deadlock_steps:
                raise DeadlockError(f"no agent ready for {deadlock_steps} steps at T={T}")
        else:
            idle = 0
        for i in moving:
            a = acts[i][done[i]]
            pos[i] = a.g
            done[i] += 1
            if done[i] == n[i]:
                arrivals[i] = T + 1
                unfinished -= 1
        T += 1
        if record_trace:
            trace.append(tuple(pos))
    return ExecResult(arrivals, sum(arrivals), max(arrivals, default=0), T, trace)


def check_trace(trace: Sequence[Sequence[Cell]]) -> List[str]:
    """Independent safety check of an executed trace. Returns a list of violations."""
    errs: List[str] = []
    for T, row in enumerate(trace):
        if len(set(row)) < len(row):
            seen = {}
            for i, c in enumerate(row):
                if c in seen:
                    errs.append(f"vertex conflict at T={T}: agents {seen[c]} and {i} at {c}")
                seen[c] = i
        if T == 0:
            continue
        prev = trace[T - 1]
        where = {c: i for i, c in enumerate(prev)}
        for i, (a, b) in enumerate(zip(prev, row)):
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) > 1:
                errs.append(f"agent {i} jumps {a}->{b} at T={T}")
            if a != b:
                j = where.get(b)
                if j is not None and j != i and row[j] == a and i < j:
                    errs.append(f"swap at T={T - 1}->{T}: agents {i} and {j} on {a}<->{b}")
        if len(errs) > 20:
            break
    return errs
