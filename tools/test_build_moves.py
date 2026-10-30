import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_moves as bm  # noqa: E402


def test_spline_hits_keys():
    keys = [(0, 0), (4, 10), (10, 2)]
    assert [round(bm.spline(keys, f), 6) for f in (0, 4, 10)] == [0, 10, 2]


def test_spline_never_overshoots_between_keys():
    # a landing: drop to 0 and stay there; the ground must not be passed
    keys = [(0, 0), (8, 14), (14, 0), (22, 0)]
    assert min(bm.spline(keys, f / 4) for f in range(0, 88)) >= 0
    assert max(bm.spline(keys, f / 4) for f in range(0, 88)) <= 14
    # travel then stop: no drifting back
    x = [(0, 0), (4, 0), (14, 8), (20, 8)]
    vals = [bm.spline(x, f / 4) for f in range(0, 80)]
    assert all(b >= a - 1e-9 for a, b in zip(vals, vals[1:]))
