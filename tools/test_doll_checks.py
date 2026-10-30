import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import doll_checks as dc  # noqa: E402


def rows(**tracks):
    n = max(len(v) for v in tracks.values())
    out = []
    for i in range(n):
        r = {"t": i * 30, "hop": 0.0, "legs": 0.0, "squash": 0.0, "x": 0.0, "face": 1.0}
        for k, v in tracks.items():
            r[k] = v[min(i, len(v) - 1)]
        out.append(r)
    return out


def test_parse_channel_dump():
    line = "30,1,0.250,-,,0,1,2,3,hop=1.5,legs=-0.2,x=3.0"
    r = dc.parse(line)
    assert r["t"] == 30 and r["hop"] == 1.5 and r["legs"] == -0.2 and r["x"] == 3.0


def test_jump_without_crouch_is_flagged():
    bad = rows(hop=[0, 0, 0, 0, 4, 8, 4, 0, 0])
    good = rows(hop=[0, 0, 0, 0, 4, 8, 4, 0, 0], legs=[0, 0.5, 1, 1, -1, -1, -1, 0.8, 0])
    assert len(dc.takeoffs_without_anticipation(bad)) == 1
    assert dc.takeoffs_without_anticipation(good) == []


def test_landing_without_squash_is_flagged():
    bad = rows(hop=[0, 4, 8, 4, 0, 0, 0])
    good = rows(hop=[0, 4, 8, 4, 0, 0, 0], squash=[0, 0, 0, 0, 0.8, 0.5, 0])
    assert len(dc.landings_without_squash(bad)) == 1
    assert dc.landings_without_squash(good) == []


def test_sliding_on_the_ground_is_flagged():
    slide = rows(x=[0, 1, 2, 3, 4])
    hop = rows(x=[0, 0, 2, 4, 4], hop=[0, 3, 6, 3, 0])
    assert len(dc.foot_slides(slide)) >= 3
    assert dc.foot_slides(hop) == []


def test_turn_on_the_ground_is_flagged():
    ground = rows(face=[1, 1, -1, -1])
    air = rows(face=[1, 1, -1, -1], hop=[0, 5, 6, 0])
    assert len(dc.ground_turns(ground)) == 1
    assert dc.ground_turns(air) == []
