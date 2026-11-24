import glob
import json
import os

from mapf.adg import build_adg, coupling_metrics, is_acyclic, path_to_actions

from .conftest import DATA, ROOT, needs_data


def test_waits_are_dropped():
    acts = path_to_actions(0, [(0, 0), (0, 0), (0, 1), (0, 1), (1, 1)])
    assert [(a.s, a.g, a.t) for a in acts] == [((0, 0), (0, 1), 1), ((0, 1), (1, 1), 3)]
    assert [a.idx for a in acts] == [0, 1]


def test_disjoint_agents_have_no_type2_edges():
    adg = build_adg([[(0, 0), (0, 1), (0, 2)], [(2, 0), (2, 1), (2, 2)]])
    assert adg.num_type2 == 0 and adg.num_type1 == 2 and adg.num_actions == 4
    m = coupling_metrics(adg)
    assert m["type2_density"] == 0 and m["coupled_agents"] == 0


def test_corridor_follow_gives_exactly_one_edge():
    # agent 0 leaves (0,1) at t=0; agent 1 enters (0,1) at t=1, then (0,2) at t=2
    paths = [[(0, 1), (0, 2), (0, 3)], [(0, 0), (0, 0), (0, 1), (0, 2)]]
    adg = build_adg(paths)
    # (0,0): leave (0,1)@0 -> first entry of agent 1 into (0,1) is its action 0 (t=1)
    # (0,1): leave (0,2)@1 -> agent 1 enters (0,2) with action 1 (t=2)
    assert adg.type2_edges() == [((0, 0), (1, 0)), ((0, 1), (1, 1))]
    # agent 1 never leaves a cell agent 0 later enters -> no edges back
    assert adg.type2_in.get((0, 0)) is None and adg.type2_in.get((0, 1)) is None
    assert is_acyclic(adg)
    m = coupling_metrics(adg)
    assert m["type2_edges"] == 2 and m["type2_density"] == 2 / 4 and m["coupled_agents"] == 2


def test_single_follow_edge():
    paths = [[(0, 1), (1, 1)], [(0, 0), (0, 0), (0, 1)]]
    assert build_adg(paths).type2_edges() == [((0, 0), (1, 0))]


def test_break_keeps_only_first_entry():
    # agent 1 enters (0,1) twice after agent 0 left it: only the first entry gets an edge
    paths = [
        [(0, 1), (1, 1), (2, 1), (2, 1), (2, 1), (2, 1), (2, 1)],
        [(0, 0), (0, 0), (0, 1), (0, 0), (0, 1), (0, 2)],
    ]
    adg = build_adg(paths)
    assert ((0, 0), (1, 0)) in adg.type2_edges()
    assert ((0, 0), (1, 2)) not in adg.type2_edges()


def test_hoenig_fig2_moves_only():
    """Moves of the Fig. 2 plan of Hönig et al. 2019 (locations as cells A..F)."""
    A, B, C, D, E, F = (0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)
    p1 = [D, D, C]
    p2 = [B, B, D, D, F]
    p3 = [A, A, B, B, D]
    adg = build_adg([p1, p2, p3])
    assert sorted(adg.type2_edges()) == sorted([
        ((0, 0), (1, 0)),  # r1 leaves D before r2 enters D
        ((0, 0), (2, 1)),  # ... and before r3 enters D
        ((1, 0), (2, 0)),  # r2 leaves B before r3 enters B
        ((1, 1), (2, 1)),  # r2 leaves D before r3 enters D
    ])
    assert is_acyclic(adg)


def test_rotation_cycle_is_detected():
    # four agents rotating around a 2x2 block in the same step (a cycle conflict)
    a, b, c, d = (0, 0), (0, 1), (1, 1), (1, 0)
    paths = [[a, b], [b, c], [c, d], [d, a]]
    assert not is_acyclic(build_adg(paths))


def _solutions():
    files = sorted(glob.glob(os.path.join(ROOT, "results", "solutions", "*.json")))
    return files


@needs_data
def test_adg_acyclic_for_benchmark_solutions():
    """Every validated benchmark solution (saved by Step 7) has an acyclic ADG.

    If Step 7 has not been run, solve a few instances on the fly instead.
    """
    files = _solutions()
    if files:
        for fn in files:
            with open(fn) as f:
                sol = json.load(f)
            assert is_acyclic(build_adg([[tuple(c) for c in p] for p in sol["paths"]])), fn
        return
    from mapf.cbs import cbs
    from mapf.io import load_instance
    from mapf.prioritized import prioritized_planning

    for name in ["empty-32-32", "random-32-32-10", "room-32-32-4"]:
        for scen in (1, 2):
            grid, s, g = load_instance(DATA, name, scen, 8)
            for solver in (cbs, prioritized_planning):
                res = solver(grid, s, g, time_limit=20)
                if res.success:
                    assert is_acyclic(build_adg(res.paths))
