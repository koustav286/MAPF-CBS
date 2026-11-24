import math
import os

from mapf.heuristics import INF, bfs_distances, octile_distance
from mapf.io import load_instance, map_path, parse_map, parse_scen, scen_path

from .conftest import DATA, needs_data

MAPS = ["empty-32-32", "random-32-32-10", "room-32-32-4"]


def test_map_parser_terrain(tmp_path):
    p = tmp_path / "t.map"
    p.write_text("type octile\nheight 2\nwidth 4\nmap\n.GS@\nOTW.\n")
    g = parse_map(str(p))
    assert (g.height, g.width) == (2, 4)
    assert g.passable == [[True, True, True, False], [False, False, False, True]]
    assert g.name == "t"


def test_scen_xy_convention(tmp_path):
    """x is the column, y is the row: '... 5 2 7 1 ...' -> start (row 2, col 5)."""
    m = tmp_path / "t.map"
    m.write_text("type octile\nheight 3\nwidth 8\nmap\n" + "........\n" * 3)
    s = tmp_path / "t.scen"
    s.write_text("version 1\n0\tt.map\t8\t3\t5\t2\t7\t1\t2.41421356\n")
    (e,) = parse_scen(str(s))
    assert e.start == (2, 5) and e.goal == (1, 7)
    g = parse_map(str(m))
    # a wide, short map: (row, col) = (2, 5) is in bounds but (5, 2) is not
    assert g.in_bounds(e.start) and not g.in_bounds((5, 2))


@needs_data
def test_benchmark_files_parse():
    for name in MAPS:
        g = parse_map(map_path(DATA, name))
        assert (g.height, g.width) == (32, 32)
        for sid in range(1, 11):
            entries = parse_scen(scen_path(DATA, name, sid))
            assert len(entries) > 100
            for e in entries[:50]:
                assert e.map_name == f"{name}.map"
                assert g.is_free(e.start) and g.is_free(e.goal)


@needs_data
def test_optimal_length_matches_octile_distance():
    """Moving AI's optimal_length is an 8-connected (octile) distance, so check against that.

    The spec suggested comparing against a 4-connected BFS, but e.g. the first row of
    empty-32-32-random-1 lists 9.414 (= 8 + sqrt 2), which no unit-cost path can have.
    We also check the 4-connected BFS distance is never shorter than the octile distance.
    """
    for name in MAPS:
        g = parse_map(map_path(DATA, name))
        for e in parse_scen(scen_path(DATA, name, 1))[:25]:
            oct_d = octile_distance(g, e.start, e.goal)
            assert math.isclose(oct_d, e.optimal_length, abs_tol=1e-4), (name, e)
            bfs = bfs_distances(g, e.goal)[g.to_id(e.start)]
            assert bfs != INF and bfs >= oct_d - 1e-9


@needs_data
def test_load_instance_first_k():
    g, starts, goals = load_instance(DATA, "empty-32-32", 1, 5)
    entries = parse_scen(scen_path(DATA, "empty-32-32", 1))
    assert starts == [e.start for e in entries[:5]] and goals == [e.goal for e in entries[:5]]
    assert len(set(starts)) == 5 and len(set(goals)) == 5
