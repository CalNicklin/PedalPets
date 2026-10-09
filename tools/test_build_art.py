import sys
from pathlib import Path

import pytest

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
    assert reactions == [("r", "{Trigger::BigHit, 0, 1500, 0, 1}")]


def test_full_step_fields():
    m = reaction(steps=[{"pose": "@current", "hold": [100, 200], "eyes": "Wide",
                         "until": "SustainEnd", "until_max": 900}],
                 moods=["IntoIt", "Hyped"], cooldown=800)
    steps, reactions = ba.build_reactions(m, POSES)
    assert steps == ["{POSE_CURRENT, 100, 200, Eye::Wide, EventType::SustainEnd, 900}"]
    assert reactions == [("r", "{Trigger::BigHit, 12, 800, 0, 1}")]


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


def test_idles_require_every_mood():
    m = {"idles": {"Asleep": ["a"], "Curious": ["a"], "IntoIt": ["b"]}}
    with pytest.raises(ba.ArtError, match="Hyped"):
        ba.build_idles(m, POSES)


def test_idles_flatten():
    m = {"idles": {"Asleep": ["a"], "Curious": ["a", "b"], "IntoIt": ["b"], "Hyped": ["a", "b"]}}
    flat, loops = ba.build_idles(m, POSES)
    assert flat == [0, 0, 1, 1, 0, 1]
    assert loops == ["{0, 1}", "{1, 2}", "{3, 1}", "{4, 2}"]


def test_sheet_frame_out_of_range():
    with pytest.raises(ba.ArtError, match="out of range"):
        ba.load_canvas("sprites/EVil Wizard 2/Sprites/Jump.png#5")


def test_missing_file():
    with pytest.raises(ba.ArtError, match="missing"):
        ba.load_canvas("art/poses/nope.png")


def test_pose_needs_eyes():
    with pytest.raises(ba.ArtError, match="eyes"):
        ba.process_pose("x", {"src": f"{IDLE_SHEET}#0"})


def test_sheet_pose_is_cropped_onto_baseline():
    p = ba.process_pose("x", {"src": f"{IDLE_SHEET}#0", "eyes": [52, 30]})
    assert p["x"] >= 0 and p["x"] + p["w"] <= 96
    assert p["y"] + p["h"] == 108  # feet on the baseline
    assert len(p["pixels"]) == p["w"] * p["h"]
    assert (p["ex"], p["ey"]) == (52, 30)


def test_baked_eyes():
    p = ba.process_pose("x", {"src": f"{IDLE_SHEET}#0", "eyes": "baked"})
    assert (p["ex"], p["ey"]) == (-1, -1)


def test_sheet_poses_expand():
    m = {"sheet_poses": [{"prefix": "idle", "src": IDLE_SHEET, "frames": [0, 2], "eyes": [1, 2]}]}
    poses = ba.collect_poses(m)
    assert list(poses) == ["idle_0", "idle_2"]
    assert poses["idle_2"]["src"] == f"{IDLE_SHEET}#2"
