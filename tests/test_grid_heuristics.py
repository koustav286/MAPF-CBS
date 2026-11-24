from mapf.grid import Grid
from mapf.heuristics import INF, HeuristicCache, bfs_distances

G = Grid.from_strings([
    "....",
    ".@@.",
    "....",
    "@...",
])


def test_neighbours_four_connected_and_blocked():
    assert sorted(G.neighbours_rc((0, 0))) == [(0, 1), (1, 0)]
    assert sorted(G.neighbours_rc((2, 1))) == [(2, 0), (2, 2), (3, 1)]
    assert G.neighbours_rc((1, 1)) == []  # blocked cell
    assert not G.is_free((-1, 0)) and not G.is_free((0, 4))


def test_valid_steps():
    assert G.is_valid_step((0, 0), (0, 0))  # wait
    assert G.is_valid_step((0, 0), (0, 1))
    assert not G.is_valid_step((0, 0), (1, 1))  # diagonal / blocked
    assert not G.is_valid_step((0, 1), (1, 1))  # into an obstacle
    assert not G.is_valid_step((0, 0), (0, 2))  # jump


def test_bfs_exact_distances():
    d = bfs_distances(G, (0, 0))
    assert d[G.to_id((0, 0))] == 0
    assert d[G.to_id((0, 3))] == 3
    assert d[G.to_id((2, 1))] == 3  # around via (1,0),(2,0)
    assert d[G.to_id((3, 3))] == 6
    assert d[G.to_id((1, 1))] == INF


def test_bfs_unreachable():
    g = Grid.from_strings([".@.", "@@.", "..."])
    assert bfs_distances(g, (0, 0))[g.to_id((2, 2))] == INF


def test_cache_reuses_tables():
    c = HeuristicCache()
    a = c.get(G, (0, 0))
    b = c.get(G, (0, 0))
    assert a is b and len(c) == 1
    c.get(G, (3, 3))
    assert len(c) == 2
