import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import build_doll as bd  # noqa: E402


def make_doll(tmp_path, parts, channels=("hop", "a", "b")):
    poses = tmp_path / "poses"
    poses.mkdir()
    for part in parts:
        for img in part["images"]:
            im = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
            x0, y0, x1, y1 = img.pop("box")
            im.paste((255, 0, 0, 255), (x0, y0, x1, y1))
            im.save(poses / img["file"])
    meta = {"palette": [{"name": "ink", "render": [0, 0, 0], "out": "#000000"},
                        {"name": "red", "render": [255, 0, 0], "out": "#ff0000"}],
            "canvas": [10, 10], "parts": parts, "draw_order": [p["name"] for p in parts][::-1],
            "channels": list(channels), "ground": parts[0]["name"]}
    (tmp_path / "parts.json").write_text(json.dumps(meta))
    return tmp_path


def two_parts():
    return [
        {"name": "base", "parent": None,
         "axes": [{"name": "s", "values": [0, 1], "sources": ["a"]}],
         "images": [{"file": "base_000.png", "box": (2, 5, 6, 10), "pivot": [4.0, 10.0],
                     "anchors": {"arm": [5.13, 5.0]}},
                    {"file": "base_001.png", "box": (2, 4, 6, 10), "pivot": [4.0, 10.0],
                     "anchors": {"arm": [5.0, 4.0]}}]},
        {"name": "arm", "parent": "base",
         "axes": [{"name": "angle", "values": [-10, 10], "sources": ["a", "b"]}],
         "images": [{"file": "arm_000.png", "box": (0, 0, 3, 3), "pivot": [1.0, 1.0], "anchors": {}},
                    {"file": "arm_001.png", "box": (1, 0, 4, 3), "pivot": [1.0, 1.0], "anchors": {}}]},
    ]


def test_tables(tmp_path):
    t = bd.build(make_doll(tmp_path, two_parts()))
    base, arm = t["parts"]
    assert base["parent"] == -1 and arm["parent"] == 0 and arm["slot"] == 0
    assert base["axes"] == [(2, 0, 0b010)]
    assert arm["axes"] == [(2, 2, 0b110)]
    assert t["axis_values"] == [0, 4, -40, 40]          # quarter units
    assert t["draw_order"] == [1, 0]
    assert t["hop"] == 0
    # crop + quarter-pixel pivot/anchors
    assert t["images"][0][:4] == (2, 5, 4, 5)
    assert t["images"][0][4:6] == (16, 40)
    assert t["anchors"][t["images"][0][6]] == (21, 20)     # 5.13 * 4 = 20.52 -> 21
    assert len(t["pixels"][0]) == 2 * 5                    # 4 px wide -> 2 bytes per row


def test_parent_must_come_first(tmp_path):
    parts = two_parts()[::-1]
    with pytest.raises(bd.DollError, match="parent"):
        bd.build(make_doll(tmp_path, parts))


def test_unknown_channel(tmp_path):
    parts = two_parts()
    parts[1]["axes"][0]["sources"] = ["nope"]
    with pytest.raises(bd.DollError, match="channel"):
        bd.build(make_doll(tmp_path, parts))


def test_emit_compiles_as_plain_cpp(tmp_path):
    t = bd.build(make_doll(tmp_path, two_parts()))
    text = bd.emit_meta(t)
    assert "static const DollTables DOLL" in text
    assert "#include <Arduino.h>" not in text
