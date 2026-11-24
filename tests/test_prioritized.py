import random

from mapf.constraints import ConstraintTable
from mapf.grid import Grid
from mapf.prioritized import prioritized_planning, reserve_path
from mapf.validator import find_errors

from .conftest import DATA, needs_data

OPEN = Grid.from_strings(["....."] * 5, name="open5")


def check(grid, starts, goals, res, forbid_following=True):
    assert res.success, res.status
    assert find_errors(grid.passable, starts, goals, res.paths, forbid_following=forbid_following) == []


def test_independent_agents_get_shortest_paths():
    starts, goals = [(0, 0), (4, 4)], [(0, 4), (4, 0)]
    res = prioritized_planning(OPEN, starts, goals)
    check(OPEN, starts, goals, res)
    assert res.soc == 8 and res.ll_searches == 2


def test_crossing_lower_priority_yields():
    starts, goals = [(2, 0), (0, 2)], [(2, 4), (4, 2)]
    res = prioritized_planning(OPEN, starts, goals)
    check(OPEN, starts, goals, res)
    assert len(res.paths[0]) - 1 == 4  # agent 0 (highest priority) is never delayed
    assert res.soc >= 9


def test_reservation_table_contents():
    t = ConstraintTable(OPEN)
    reserve_path(t, [(0, 0), (0, 1), (0, 2)])
    c = OPEN.to_id
    assert t.vertex[c((0, 1))] == {0, 1, 2}  # t-1, t, t+1 under the no-following model
    assert t.permanent[c((0, 2))] == 1


def test_higher_priority_goal_blocks_corridor_fails():
    corr = Grid.from_strings([".....", "@@@@@"], name="corr")
    # agent 0 parks in the middle of the corridor; agent 1 must cross it -> PP fails
    res = prioritized_planning(corr, [(0, 1), (0, 0)], [(0, 2), (0, 4)])
    assert res.status == "no_solution" and res.extra["failed_agent"] == 1


def test_order_matters_but_never_invalid():
    rng = random.Random(3)
    cells = list(OPEN.free_cells())
    for _ in range(30):
        pts = rng.sample(cells, 8)
        starts, goals = pts[:4], pts[4:]
        for ff in (True, False):
            res = prioritized_planning(OPEN, starts, goals, forbid_following=ff)
            if res.success:
                check(OPEN, starts, goals, res, forbid_following=ff)


@needs_data
def test_benchmark_instance_valid():
    from mapf.io import load_instance

    solved = 0
    for scen in range(1, 6):
        grid, starts, goals = load_instance(DATA, "random-32-32-10", scen, 20)
        res = prioritized_planning(grid, starts, goals, time_limit=30)
        if res.success:
            solved += 1
            check(grid, starts, goals, res)
        else:
            assert res.extra["reason"] in ("start_blocked", "no_path")
    assert solved >= 2


def test_start_blocked_reason():
    corr = Grid.from_strings([".....", "@@@@@"], name="corr")
    # agent 0 walks right through agent 1's start at t=1: a following conflict nobody can fix
    res = prioritized_planning(corr, [(0, 0), (0, 1)], [(0, 4), (0, 3)])
    assert res.status == "no_solution" and res.extra["reason"] == "start_blocked"
