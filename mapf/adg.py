"""Action Dependency Graph (Hönig, Kiesel, Tinka, Durham, Ayanian 2019).

Each agent's path is turned into move actions only (waits are dropped). Action k of agent i is
(s, g, t): it moves s -> g and starts at timestep t of the original plan.

* Type 1 edges: (i, k) -> (i, k+1).
* Type 2 edges, as in Algorithm 1 of the paper: for every action (i, k) and every other agent
  j, add (i, k) -> (j, l) for the *first* l (in j's order) with s(i,k) == g(j,l) and
  t(i,k) <= t(j,l), then stop looking at j (the paper's ``break``). Meaning: j may move into the
  cell only after i has moved out of it, in the order the plan used. Later entries of j into
  that cell are already ordered after it through j's Type 1 chain.

Type 2 edges are found per cell (actions grouped by the cell they enter, per agent, sorted by
time, then a binary search), so the cost does not grow with every pair of actions on the map.
"""
from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

Cell = Tuple[int, int]
ActionId = Tuple[int, int]  # (agent, index)


@dataclass(frozen=True)
class Action:
    agent: int
    idx: int
    s: Cell
    g: Cell
    t: int


@dataclass
class ADG:
    actions: List[List[Action]]
    type2_out: Dict[ActionId, List[ActionId]] = field(default_factory=dict)
    type2_in: Dict[ActionId, List[ActionId]] = field(default_factory=dict)

    @property
    def num_agents(self) -> int:
        return len(self.actions)

    @property
    def num_actions(self) -> int:
        return sum(len(a) for a in self.actions)

    @property
    def num_type1(self) -> int:
        return sum(max(0, len(a) - 1) for a in self.actions)

    @property
    def num_type2(self) -> int:
        return sum(len(v) for v in self.type2_out.values())

    def type2_edges(self) -> List[Tuple[ActionId, ActionId]]:
        return [(u, v) for u, vs in sorted(self.type2_out.items()) for v in vs]


def path_to_actions(agent: int, path: Sequence[Cell]) -> List[Action]:
    out: List[Action] = []
    for t in range(len(path) - 1):
        a, b = tuple(path[t]), tuple(path[t + 1])
        if a != b:
            out.append(Action(agent, len(out), a, b, t))
    return out


def build_adg(paths: Sequence[Sequence[Cell]]) -> ADG:
    actions = [path_to_actions(i, p) for i, p in enumerate(paths)]
    # enters[cell][j] = (sorted start times, action indices) of j's actions entering cell
    enters: Dict[Cell, Dict[int, Tuple[List[int], List[int]]]] = defaultdict(dict)
    for j, acts in enumerate(actions):
        for a in acts:  # already sorted by time
            ts, ls = enters[a.g].setdefault(j, ([], []))
            ts.append(a.t)
            ls.append(a.idx)
    adg = ADG(actions)
    for i, acts in enumerate(actions):
        for a in acts:
            by_agent = enters.get(a.s)
            if not by_agent:
                continue
            for j in sorted(by_agent):
                if j == i:
                    continue
                ts, ls = by_agent[j]
                pos = bisect_left(ts, a.t)  # first entry with t(j,l) >= t(i,k)
                if pos < len(ts):
                    u, v = (i, a.idx), (j, ls[pos])
                    adg.type2_out.setdefault(u, []).append(v)
                    adg.type2_in.setdefault(v, []).append(u)
    return adg


def is_acyclic(adg: ADG) -> bool:
    """Kahn's algorithm over Type 1 + Type 2 edges."""
    indeg: Dict[ActionId, int] = {}
    succ: Dict[ActionId, List[ActionId]] = defaultdict(list)
    for acts in adg.actions:
        for a in acts:
            indeg.setdefault((a.agent, a.idx), 0)
        for a, b in zip(acts, acts[1:]):
            succ[(a.agent, a.idx)].append((b.agent, b.idx))
            indeg[(b.agent, b.idx)] += 1
    for u, vs in adg.type2_out.items():
        for v in vs:
            succ[u].append(v)
            indeg[v] += 1
    q = deque(u for u, d in indeg.items() if d == 0)
    seen = 0
    while q:
        u = q.popleft()
        seen += 1
        for v in succ[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return seen == len(indeg)


def coupling_metrics(adg: ADG) -> Dict[str, float]:
    """Type-2 edge count, Type-2 edges per action ("density"), agents linked to another agent."""
    linked = set()
    for (i, _), vs in adg.type2_out.items():
        for (j, _) in vs:
            linked.add(i)
            linked.add(j)
    n_act = adg.num_actions
    e2 = adg.num_type2
    return {
        "num_actions": n_act,
        "type2_edges": e2,
        "type2_density": e2 / n_act if n_act else 0.0,
        "coupled_agents": len(linked),
        "coupled_fraction": len(linked) / adg.num_agents if adg.num_agents else 0.0,
    }
