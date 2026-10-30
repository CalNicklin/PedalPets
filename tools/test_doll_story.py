import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import doll_story as ds  # noqa: E402


def row(t, mood, rx, thought):
    return {"t_ms": str(t), "mood": str(mood), "reaction": rx, "thought": thought}


def test_one_line_per_change():
    rows = [row(0, 1, "-", "looking around"), row(30, 1, "-", "looking around"),
            row(60, 1, "-", "bored - pecking about"), row(90, 2, "startle", "grooving with you")]
    lines = ds.story(rows)
    assert len(lines) == 3
    assert "bored" in lines[1] and "[startle]" in lines[2] and "IntoIt" in lines[2]
