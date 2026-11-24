import heapq
import itertools
import random

import pytest

from mapf.cbs import cbs, detect_conflicts
from mapf.grid import Grid
from mapf.prioritized import prioritized_planning
from mapf.validator import find_errors

from .conftest import DATA, needs_data


def joint_optimal_soc(grid, starts, goals, forbid_following=True, cap=6):
    """Brute-force optimal SOC by Dijkstra over the joint state space.

    State = (positions, goal-wait counters). An agent standing on its goal defers the cost of
    that step; if it later leaves, it pays the deferred steps. When all agents are on their
    goals the remaining deferred steps are never paid, which matches the SOC convention
    (arrival time ignoring trailing waits). Counters above ``cap`` are pruned (fine on 4x4).
    """
    k = len(starts)
    starts, goals = tuple(starts), tuple(goals)
    opts = lambda c: [c] + grid.neighbours_rc(c)
    start_state = (starts, (0,) * k)
    dist = {start_state: 0}
    pq = [(0, 0, start_state)]
    tie = itertools.count()
    while pq:
        d, _, (pos, cnt) = heapq.heappop(pq)
        if d > dist[(pos, cnt)]:
            continue
        if pos == goals:
            return d
        for nxt in itertools.product(*(opts(c) for c in pos)):
            if len(set(nxt)) < k:
                continue
            bad = False
            for i in range(k):
                for j in range(k):
                    if i == j:
                        continue
                    if forbid_following and nxt[i] != pos[i] and nxt[i] == pos[j]:
                        bad = True
                    if not forbid_following and nxt[i] == pos[j] and nxt[j] == pos[i] and nxt[i] != pos[i]:
                        bad = True
            if bad:
                continue
            nd, ncnt = d, []
            for i in range(k):
                if pos[i] == goals[i] and nxt[i] == goals[i]:  # resting on the goal: defer
                    ncnt.append(cnt[i] + 1)
                else:
                    nd += 1 + cnt[i]
                    ncnt.append(0)
            if max(ncnt) > cap:
                continue
            st = (tuple(nxt), tuple(ncnt))
            if nd < dist.get(st, 10**9):
                dist[st] = nd
                heapq.heappush(pq, (nd, next(tie), st))
    return None


def valid(grid, starts, goals, res, ff=True):
    assert res.success, res.status
    assert find_errors(grid.passable, starts, goals, res.paths, forbid_following=ff) == []


@pytest.mark.parametrize("ff", [True, False])
def test_corridor_swap_with_side_pocket(ff):
    g = Grid.from_strings([".....", "@@.@@"], name="pocket")
    starts, goals = [(0, 0), (0, 4)], [(0, 4), (0, 0)]
    res = cbs(g, starts, goals, forbid_following=ff)
    valid(g, starts, goals, res, ff)
    assert any((1, 2) in p for p in res.paths)  # someone ducks into the pocket
    assert res.soc == joint_optimal_soc(g, starts, goals, ff)
    assert prioritized_planning(g, starts, goals, forbid_following=ff).status == "no_solution"


def test_corridor_swap_without_pocket_is_unsolvable():
    g = Grid.from_strings(["...."], name="corr")
    res = cbs(g, [(0, 0), (0, 3)], [(0, 3), (0, 0)], time_limit=2)
    assert not res.success


@pytest.mark.parametrize("ff", [True, False])
def test_two_agents_crossing(ff):
    g = Grid.from_strings(["....."] * 5, name="open5")
    starts, goals = [(2, 0), (0, 2)], [(2, 4), (4, 2)]
    res = cbs(g, starts, goals, forbid_following=ff)
    valid(g, starts, goals, res, ff)
    # vertex+swap: one agent waits once (9). No-following: it may only enter the centre two
    # steps after the other agent was there, so it loses 2 steps (10).
    assert res.soc == (10 if ff else 9) == joint_optimal_soc(g, starts, goals, ff)
    assert res.hl_expanded >= 2 and res.ll_searches >= 3


def test_detect_conflicts_kinds():
    vert = [[(0, 0), (0, 1)], [(0, 2), (0, 1)]]
    assert detect_conflicts(vert)[0][0] == "vertex"
    follow = [[(0, 0), (0, 1), (0, 2)], [(0, 1), (0, 2), (0, 3)]]
    first, n = detect_conflicts(follow)
    assert first == ("following", 0, 1, (0, 1), 1) and n == 2
    assert detect_conflicts(follow, forbid_following=False) == (None, 0)
    swap = [[(0, 0), (0, 1)], [(0, 1), (0, 0)]]
    assert detect_conflicts(swap, forbid_following=False)[0][0] == "swap"
    assert detect_conflicts(swap)[0][0] == "following"


@pytest.mark.parametrize("ff", [True, False])
def test_optimality_against_joint_search(ff):
    rng = random.Random(7 if ff else 8)
    maps = [
        Grid.from_strings(["...."] * 4, name="o4"),
        Grid.from_strings(["....", ".@..", "..@.", "...."], name="b4"),
        Grid.from_strings(["..@.", "....", "@...", "..@."], name="c4"),
    ]
    checked = 0
    for trial in range(36):
        g = maps[trial % 3]
        k = 2 if trial < 18 else 3
        cells = list(g.free_cells())
        pts = rng.sample(cells, 2 * k)
        starts, goals = pts[:k], pts[k:]
        ref = joint_optimal_soc(g, starts, goals, ff)
        res = cbs(g, starts, goals, time_limit=20, forbid_following=ff)
        if ref is None:
            assert not res.success
            continue
        valid(g, starts, goals, res, ff)
        assert res.soc == ref, (g.name, starts, goals)
        checked += 1
    assert checked >= 25


@needs_data
def test_benchmark_instances_valid_and_no_worse_than_pp():
    from mapf.io import load_instance

    for name in ["empty-32-32", "random-32-32-10", "room-32-32-4"]:
        grid, starts, goals = load_instance(DATA, name, 1, 6)
        res = cbs(grid, starts, goals, time_limit=30)
        valid(grid, starts, goals, res)
        pp = prioritized_planning(grid, starts, goals)
        if pp.success:
            assert res.soc <= pp.soc
