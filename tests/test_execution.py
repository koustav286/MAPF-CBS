import random

import pytest

from mapf.adg import build_adg
from mapf.cbs import cbs
from mapf.execution import DeadlockError, check_trace, simulate
from mapf.grid import Grid
from mapf.prioritized import prioritized_planning
from mapf.validator import sum_of_costs

from .conftest import DATA, needs_data


class Scripted:
    """Stand-in RNG: returns scripted values in order, then 1.0 (never delayed)."""

    def __init__(self, values):
        self.values = list(values)

    def random(self):
        return self.values.pop(0) if self.values else 1.0


def run(paths, **kw):
    starts = [p[0] for p in paths]
    return simulate(build_adg(paths), starts, **kw)


def test_p0_no_waits_reproduces_plan():
    paths = [[(0, 0), (0, 1), (0, 2)], [(2, 0), (2, 1), (2, 2), (2, 3)]]
    r = run(paths)
    assert r.arrivals == [2, 3] and r.exec_soc == sum_of_costs(paths)
    assert check_trace(r.trace) == []


def test_p0_drops_waits():
    # agent 1 waits two steps for no reason in the plan
    paths = [[(0, 0), (0, 1)], [(2, 0), (2, 0), (2, 0), (2, 1)]]
    r = run(paths)
    assert r.arrivals == [1, 1] and r.exec_soc < sum_of_costs(paths)


def test_corridor_follow_waits_for_delayed_leader():
    # agent 0 leads, agent 1 follows one cell behind with a one-step gap (no following move)
    paths = [[(0, 1), (0, 2), (0, 3)], [(0, 0), (0, 0), (0, 1), (0, 2)]]
    base = run(paths)
    # the follower's planned wait is *needed*: it may only enter (0,1) after the leader's move out
    # of it completes, so p=0 reproduces the plan exactly
    assert base.arrivals == [2, 3]
    # leader frozen for its first ready step (draw 0.0 < p); follower is not ready yet then
    r = run(paths, p=0.5, rng=Scripted([0.0]))
    # T=0: leader frozen; follower blocked (needs leader to leave (0,1))
    # T=1: leader moves to (0,2); follower still blocked
    # T=2: leader moves to (0,3), follower enters (0,1)  T=3: follower enters (0,2)
    assert r.arrivals == [3, 4]
    assert [row[1] for row in r.trace] == [(0, 0), (0, 0), (0, 0), (0, 1), (0, 2)]
    assert check_trace(r.trace) == []


def test_burst_model_freezes_for_D_steps():
    paths = [[(0, 0), (0, 1), (0, 2)]]
    r = run(paths, p=0.5, model="burst", burst_len=5, rng=Scripted([0.0]))
    assert r.arrivals == [7]  # frozen T=0..4, moves at T=5 and T=6


def test_deadlock_guard_on_cyclic_adg():
    a, b, c, d = (0, 0), (0, 1), (1, 1), (1, 0)
    with pytest.raises(DeadlockError):
        run([[a, b], [b, c], [c, d], [d, a]], deadlock_steps=10)


def test_checker_catches_conflicts():
    assert check_trace([((0, 0), (0, 2)), ((0, 1), (0, 1))])  # vertex
    assert check_trace([((0, 0), (0, 1)), ((0, 1), (0, 0))])  # swap
    assert check_trace([((0, 0),), ((0, 2),)])  # jump
    assert check_trace([((0, 0), (0, 1)), ((0, 1), (0, 2))]) == []  # following is physically safe


def _random_solutions():
    g = Grid.from_strings(["......", ".@..@.", "......", "..@...", "......"], name="small")
    rng = random.Random(11)
    cells = list(g.free_cells())
    out = []
    for _ in range(25):
        pts = rng.sample(cells, 10)
        starts, goals = pts[:5], pts[5:]
        for solver in (cbs, prioritized_planning):
            res = solver(g, starts, goals, time_limit=5)
            if res.success:
                out.append(res.paths)
    return out


def test_p0_valid_and_not_worse_than_plan():
    sols = _random_solutions()
    assert len(sols) >= 20
    for paths in sols:
        r = run(paths)
        assert check_trace(r.trace) == []
        assert r.exec_soc <= sum_of_costs(paths)
        for i, p in enumerate(paths):
            assert r.trace[-1][i] == p[-1]


@pytest.mark.parametrize("model", ["per_step", "burst"])
def test_delayed_executions_are_safe_and_slower(model):
    for n, paths in enumerate(_random_solutions()):
        base = run(paths).exec_soc
        for p in (0.1, 0.3):
            r = run(paths, p=p, model=model, rng=random.Random(n * 100 + int(p * 10)))
            assert check_trace(r.trace) == []
            assert r.exec_soc >= base
            assert all(r.trace[-1][i] == q[-1] for i, q in enumerate(paths))


@needs_data
def test_benchmark_instance_delayed_execution():
    from mapf.io import load_instance

    grid, s, g = load_instance(DATA, "random-32-32-10", 2, 10)
    res = cbs(grid, s, g, time_limit=30)
    assert res.success
    for seed in range(5):
        r = simulate(build_adg(res.paths), s, p=0.2, rng=random.Random(seed))
        assert check_trace(r.trace) == []
