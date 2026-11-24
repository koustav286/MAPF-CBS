import time

import pytest

from mapf.astar import SearchTimeout, space_time_astar
from mapf.constraints import ConstraintTable, EdgeConstraint, VertexConstraint
from mapf.grid import Grid
from mapf.heuristics import bfs_distances

OPEN = Grid.from_strings(["....."] * 5, name="open5")
CORRIDOR = Grid.from_strings([".....", "@@@@@"], name="corr")


def cost(path):
    return len(path) - 1


def test_unconstrained_equals_bfs():
    g = Grid.from_strings([".....", ".@@@.", ".@...", ".@.@.", "....."], name="maze")
    for start in g.free_cells():
        for goal in [(0, 0), (2, 2), (4, 4)]:
            p = space_time_astar(g, start, goal)
            assert p[0] == start and p[-1] == goal
            assert cost(p) == bfs_distances(g, goal)[g.to_id(start)]
            assert all(g.is_valid_step(a, b) for a, b in zip(p, p[1:]))


def test_start_equals_goal():
    assert space_time_astar(OPEN, (2, 2), (2, 2)) == [(2, 2)]


def test_vertex_constraint_forces_wait_in_corridor():
    ct = ConstraintTable(CORRIDOR)
    ct.add_vertex((0, 1), 1)
    p = space_time_astar(CORRIDOR, (0, 0), (0, 4), ct)
    assert cost(p) == 5  # one wait somewhere before (0,1)
    assert p[1] != (0, 1)


def test_vertex_constraint_forces_detour_or_wait_in_open():
    ct = ConstraintTable(OPEN)
    ct.add_vertex((0, 1), 1)
    p = space_time_astar(OPEN, (0, 0), (0, 2), ct)
    assert p[1] != (0, 1)
    assert cost(p) == 3  # 2 + one extra step (wait or detour)


def test_edge_constraint():
    ct = ConstraintTable.from_constraints(CORRIDOR, [EdgeConstraint(0, (0, 0), (0, 1), 1)])
    p = space_time_astar(CORRIDOR, (0, 0), (0, 2), ct)
    assert p[:2] != [(0, 0), (0, 1)]
    assert cost(p) == 3


def test_goal_constraint_delays_finish():
    ct = ConstraintTable.from_constraints(OPEN, [VertexConstraint(0, (0, 2), 7)])
    p = space_time_astar(OPEN, (0, 0), (0, 2), ct)
    assert p[-1] == (0, 2) and cost(p) == 8
    assert p[7] != (0, 2)


def test_permanent_block():
    # a higher-priority agent rests at (0,2) from t=3: we can still slip past at t=2
    ct = ConstraintTable(CORRIDOR)
    ct.add_permanent((0, 2), 3)
    p = space_time_astar(CORRIDOR, (0, 0), (0, 4), ct)
    assert cost(p) == 4 and p[2] == (0, 2)
    # resting from t=1: the corridor is cut for good
    ct = ConstraintTable(CORRIDOR)
    ct.add_permanent((0, 2), 1)
    assert space_time_astar(CORRIDOR, (0, 0), (0, 4), ct) is None
    assert cost(space_time_astar(CORRIDOR, (0, 0), (0, 1), ct)) == 1
    # a permanently blocked goal can never be reached for good
    assert space_time_astar(CORRIDOR, (0, 0), (0, 2), ct) is None


def test_infeasible_terminates():
    g = Grid.from_strings(["..@.."], name="split")
    assert space_time_astar(g, (0, 0), (0, 4)) is None
    ct = ConstraintTable(CORRIDOR)
    for t in range(0, 50):
        ct.add_vertex((0, 4), t)
    ct.add_permanent((0, 4), 50)
    assert space_time_astar(CORRIDOR, (0, 0), (0, 4), ct) is None


def test_start_vertex_constraint_is_infeasible():
    ct = ConstraintTable(OPEN)
    ct.add_vertex((0, 0), 0)
    assert space_time_astar(OPEN, (0, 0), (4, 4), ct) is None


def test_timeout_raises():
    big = Grid.from_strings(["." * 60] * 60, name="big")
    ct = ConstraintTable(big)
    for t in range(2000):
        ct.add_vertex((59, 59), t)
    with pytest.raises(SearchTimeout):
        space_time_astar(big, (0, 0), (59, 59), ct, deadline=time.monotonic() - 1)
