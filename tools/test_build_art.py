import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import build_art as ba  # noqa: E402

POSES = {"a": 0, "b": 1}
IDLE_SHEET = "sprites/EVil Wizard 2/Sprites/Idle.png"


def reaction(**overrides):
    r = {"id": "r", "trigger": "BigHit", "steps": [{"pose": "a", "hold": 100}]}
    r.update(overrides)
    return {"reactions": [r]}


def test_basic_reaction_defaults():
    steps, reactions = ba.build_reactions(reaction(), POSES)
    assert steps == ["{0, 100, 100, Eye::Auto, EventType::None, 5000}"]
    assert reactions == [("r", "{Trigger::BigHit, 0, 1500, 0, 1, 0, 0, EventType::None, 5000, nullptr}")]


def test_full_step_fields():
    m = reaction(steps=[{"pose": "@current", "hold": [100, 200], "eyes": "Wide",
                         "until": "SustainEnd", "until_max": 900}],
                 moods=["IntoIt", "Hyped"], cooldown=800)
    steps, reactions = ba.build_reactions(m, POSES)
    assert steps == ["{POSE_CURRENT, 100, 200, Eye::Wide, EventType::SustainEnd, 900}"]
    assert reactions == [("r", "{Trigger::BigHit, 12, 800, 0, 1, 0, 0, EventType::None, 5000, nullptr}")]


def test_unknown_pose():
    with pytest.raises(ba.ArtError, match="unknown pose 'zzz'"):
        ba.build_reactions(reaction(steps=[{"pose": "zzz", "hold": 1}]), POSES)


@pytest.mark.parametrize("field,value,msg", [
    ("trigger", "Sneeze", "trigger"),
    ("moods", ["Grumpy"], "mood"),
    ("steps", [{"pose": "a", "hold": [300, 100]}], "hold"),
    ("steps", [{"pose": "a", "hold": 100, "eyes": "Squint"}], "eyes"),
    ("steps", [{"pose": "a", "hold": 100, "until": "Sneeze"}], "until"),
    ("steps", [], "no steps"),
])
def test_invalid_reaction_fields(field, value, msg):
    with pytest.raises(ba.ArtError, match=msg):
        ba.build_reactions(reaction(**{field: value}), POSES)


def idle(poses, period=100):
    return {"poses": poses, "period": period}


def test_idles_require_every_mood():
    m = {"idles": {"Asleep": idle(["a"]), "Curious": idle(["a"]), "IntoIt": idle(["b"])}}
    with pytest.raises(ba.ArtError, match="Hyped"):
        ba.build_idles(m, POSES)


def test_idles_require_period():
    m = {"idles": {mood: {"poses": ["a"]} for mood in ba.MOODS}}
    with pytest.raises(ba.ArtError, match="period"):
        ba.build_idles(m, POSES)


def test_idles_flatten():
    m = {"idles": {"Asleep": idle(["a"], 900), "Curious": idle(["a", "b"], 125),
                   "IntoIt": idle(["b"]), "Hyped": idle(["a", "b"], 80)}}
    flat, loops = ba.build_idles(m, POSES)
    assert flat == [0, 0, 1, 1, 0, 1]
    assert loops == ["{0, 1, 900}", "{1, 2, 125}", "{3, 1, 100}", "{4, 2, 80}"]


LAYOUT = ba.layout({"canvas": {"w": 160, "h": 128, "baseline": 122},
                    "sheets": {"frame": 250, "feet": [136, 167]}})


def test_default_layout_is_spec_canvas():
    d = ba.layout({})
    assert (d["w"], d["h"], d["baseline"]) == (96, 112, 108)


def test_sheet_frame_out_of_range():
    with pytest.raises(ba.ArtError, match="out of range"):
        ba.load_canvas("sprites/EVil Wizard 2/Sprites/Jump.png#5", LAYOUT)


def test_missing_file():
    with pytest.raises(ba.ArtError, match="missing"):
        ba.load_canvas("art/poses/nope.png", LAYOUT)


def test_png_must_match_canvas():
    with pytest.raises(ba.ArtError, match="160x128"):
        ba.load_canvas("sprites/EVil Wizard 2/Sprites/Jump.png", LAYOUT)


def test_pose_needs_eyes():
    with pytest.raises(ba.ArtError, match="eyes"):
        ba.process_pose("x", {"src": f"{IDLE_SHEET}#0"}, LAYOUT)


def test_sheet_pose_is_centred_on_baseline():
    p = ba.process_pose("x", {"src": f"{IDLE_SHEET}#0", "eyes": [52, 30]}, LAYOUT)
    assert p["x"] > 0 and p["x"] + p["w"] < 160         # not clipped
    assert abs((p["x"] + p["w"] / 2) - 80) <= 4         # body centred
    assert p["y"] + p["h"] == 122                        # feet on the baseline
    assert len(p["pixels"]) == p["w"] * p["h"]
    assert (p["ex"], p["ey"]) == (52, 30)


def test_baked_eyes():
    p = ba.process_pose("x", {"src": f"{IDLE_SHEET}#0", "eyes": "baked"}, LAYOUT)
    assert (p["ex"], p["ey"]) == (-1, -1)


def test_sheet_poses_expand():
    m = {"sheet_poses": [{"prefix": "idle", "src": IDLE_SHEET, "frames": [0, 2], "eyes": [1, 2]}]}
    poses = ba.collect_poses(m)
    assert list(poses) == ["idle_0", "idle_2"]
    assert poses["idle_2"]["src"] == f"{IDLE_SHEET}#2"


def test_reaction_loop_fields():
    m = reaction(steps=[{"pose": "a", "hold": 30}] * 4, loop_from=1, loop_len=2,
                 loop_until="SustainEnd", loop_max=6000)
    _, reactions = ba.build_reactions(m, POSES)
    assert reactions == [("r", "{Trigger::BigHit, 0, 1500, 0, 4, 1, 2, EventType::SustainEnd, 6000, nullptr}")]


def test_reaction_loop_must_fit_steps():
    m = reaction(steps=[{"pose": "a", "hold": 30}] * 2, loop_from=1, loop_len=2)
    with pytest.raises(ba.ArtError, match="loop"):
        ba.build_reactions(m, POSES)


def test_palette_parse_and_rgb565():
    pal = ba.palette({"palette": {"colors": ["#000000", "#ff0000"]}})
    assert pal == [(0, 0, 0), (255, 0, 0)]
    assert ba.palette({}) is None
    assert ba.to_rgb565(255, 0, 0) == 0x001F       # R/B swapped for the BGR panel


def test_pal4_packing_and_transparency():
    img = Image.new("RGBA", (3, 2), (0, 0, 0, 0))
    img.putpixel((0, 0), (255, 0, 0, 255))
    img.putpixel((2, 1), (0, 0, 0, 255))
    data = ba.pack_pal4(img, [(0, 0, 0), (255, 0, 0)], "x")
    # Row stride 2 bytes; index 0 = transparent, palette entries from 1.
    assert data == [0x20, 0x00, 0x00, 0x10]


def test_pal4_rejects_off_palette_colour():
    img = Image.new("RGBA", (1, 1), (10, 200, 10, 255))
    with pytest.raises(ba.ArtError, match="not in the palette"):
        ba.pack_pal4(img, [(0, 0, 0)], "x")


def test_entry_window_names_a_table():
    m = reaction(steps=[{"pose": "a", "hold": 30}, {"pose": "b", "hold": 30}], entry_window=2)
    _, reactions, entries = ba.build_reactions(m, POSES, with_entries=True)
    assert reactions[0][1].endswith(", ENTRY_0}")
    assert entries == [("ENTRY_0", [0, 1])]


def test_entry_table_picks_most_similar_step():
    def canvas(box):
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        img.paste((255, 0, 0, 255), box)
        return img
    imgs = [canvas((0, 0, 5, 10)),      # pose 0: left half
            canvas((5, 0, 10, 10)),     # pose 1: right half
            canvas((4, 0, 10, 10))]     # pose 2: nearly the right half
    # Reaction steps show poses 0 then 1.
    assert ba.entry_table(imgs, [0, 1]) == [0, 1, 1]
