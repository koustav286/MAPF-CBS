from mapf.grid import Grid
from mapf.validator import find_errors, is_valid, makespan, path_cost, sum_of_costs

G = Grid.from_strings([
    ".....",
    ".@.@.",
    ".....",
])
P = G.passable


def errs(starts, goals, paths, **kw):
    return find_errors(P, starts, goals, paths, **kw)


def test_valid_solution_with_padding():
    paths = [
        [(0, 0), (0, 1), (0, 2)],
        [(2, 4), (2, 3), (2, 2), (2, 1), (2, 0)],
    ]
    assert errs([(0, 0), (2, 4)], [(0, 2), (2, 0)], paths) == []
    assert sum_of_costs(paths) == 6 and makespan(paths) == 4


def test_path_cost_ignores_trailing_waits_only():
    assert path_cost([(0, 0), (0, 1), (0, 1), (0, 1)]) == 1
    assert path_cost([(0, 0), (0, 0), (0, 1)]) == 2  # leading wait counts
    assert path_cost([(0, 0)]) == 0


def test_wrong_start_and_goal():
    e = errs([(0, 0)], [(0, 2)], [[(0, 1), (0, 2)]])
    assert any("starts at" in x for x in e)
    e = errs([(0, 0)], [(0, 2)], [[(0, 0), (0, 1)]])
    assert any("ends at" in x for x in e)


def test_illegal_moves():
    assert any("illegal move" in x for x in errs([(0, 0)], [(0, 2)], [[(0, 0), (0, 2)]]))
    assert any("illegal move" in x for x in errs([(0, 0)], [(2, 2)], [[(0, 0), (1, 0), (2, 1), (2, 2)]]))  # diagonal
    assert any("blocked" in x for x in errs([(0, 0)], [(2, 1)], [[(0, 0), (0, 1), (1, 1), (2, 1)]]))
    assert any("blocked" in x for x in errs([(0, 0)], [(0, 0)], [[(0, 0), (-1, 0), (0, 0)]]))


def test_vertex_conflict():
    paths = [[(0, 0), (0, 1), (0, 2)], [(0, 4), (0, 3), (0, 2)]]
    e = errs([(0, 0), (0, 4)], [(0, 2), (0, 2)], paths)
    assert any("vertex conflict" in x for x in e)


def test_swap_conflict():
    paths = [[(0, 0), (0, 1)], [(0, 1), (0, 0)]]
    e = errs([(0, 0), (0, 1)], [(0, 1), (0, 0)], paths, forbid_following=False)
    assert any("swap conflict" in x for x in e)


def test_following_conflict_depends_on_model():
    # convoy: agent 1 leads, agent 0 follows into the cell agent 1 just left
    paths = [[(0, 0), (0, 1), (0, 2)], [(0, 1), (0, 2), (0, 3)]]
    starts, goals = [(0, 0), (0, 1)], [(0, 2), (0, 3)]
    assert any("following conflict" in x for x in errs(starts, goals, paths))
    assert errs(starts, goals, paths, forbid_following=False) == []
    # with a one-step gap it is fine in both models
    paths = [[(0, 0), (0, 0), (0, 1), (0, 2)], [(0, 1), (0, 2), (0, 3)]]
    assert errs(starts, goals, paths) == []


def test_premature_goal_departure_and_goal_occupation():
    # agent 0 finishes at (0,2) at t=2; agent 1 later walks through (0,2) at t=4
    paths = [
        [(0, 0), (0, 1), (0, 2)],
        [(2, 2), (2, 2), (2, 2), (2, 2), (1, 2), (0, 2), (0, 3)],
    ]
    e = errs([(0, 0), (2, 2)], [(0, 2), (0, 3)], paths)
    assert any("vertex conflict" in x and "(0, 2)" in x for x in e)


def test_is_valid_shortcut():
    assert is_valid(P, [(0, 0)], [(0, 1)], [[(0, 0), (0, 1)]])
    assert not is_valid(P, [(0, 0)], [(0, 1)], [[(0, 0)]])
