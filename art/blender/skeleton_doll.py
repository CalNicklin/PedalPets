"""The skeleton as a paper doll: each part rendered on its own over its pose
range, with 2D attachment points. See docs/superpowers/specs/2026-10-30-packs-and-skeleton-design.md.

  /Applications/Blender.app/Contents/MacOS/Blender -b -P art/blender/skeleton_doll.py -- <out_dir> [part ...]

Arms render in the screen plane (see skeleton.py): an upper arm image per
shoulder angle, a forearm image per world angle (shoulder + elbow) and hand
shape. Angles: 0 hanging, + toward the way he faces, 180 up.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import skeleton as sk  # noqa: E402


def rng(lo, hi, step):
    return [lo + i * step for i in range(int(round((hi - lo) / step)) + 1)]


BENDS = [-1] + rng(0, 3, 0.25)            # -1 tucked (airborne), 0 stand .. 2 low, 3 lying
STRIDES = [-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1]
LEANS = rng(-96, 24, 3)                   # past -24 the body rolls back across the picture
SHAPES = {-1: (0.94, 1.0, 1.07), -0.5: (0.97, 1.0, 1.035), 0: (1.0, 1.0, 1.0), 0.5: (1.03, 1.0, 0.965),
          1: (1.06, 1.0, 0.93), 1.5: (1.08, 1.0, 0.9), 2: (1.1, 1.0, 0.87)}
EYES = {-1: ("wide", (1.45, 1, 1.45)), 0: ("open", (1, 1, 1)), 1: ("half", (1, 1, 0.45)),
        2: ("closed", (0.01, 0.01, 0.01))}   # closed: empty sockets
LOOKS = rng(-30, 45, 15)                  # 45 turns the skull to the viewer
UPPER_ANGLES = rng(-180, 180, 12)
FORE_ANGLES = rng(-228, 228, 12)          # shoulder + elbow can pass straight up
HANDS = [0, 1, 2]                         # open, fist, point


def look(l):
    return (0.7 * max(-30, min(30, l)), l)


def legs_pose(bend, stride):
    return sk.legs_pose(bend, stride)


def roll_and(lean):
    """The body/head tilt split into a 3/4 lean and a roll across the picture (skeleton.tilt)."""
    x, roll = sk.tilt(lean)
    return x, {"roll": {"r": (0, -roll, 0)}}


def body_pose(lean, shape):
    x, roll = roll_and(lean)
    return sk.merge(roll, {"hips": {"r": (x, 0, 0), "s": SHAPES[shape]}})


def skull_pose(pitch, lk, eyes):
    ry, rz = look(lk)
    s = EYES[eyes][1]
    x, roll = roll_and(pitch)
    return sk.merge(roll, {"head": {"r": (x, ry, rz)}, "eyeR": {"s": s}, "eyeL": {"s": s}})


def jaw_pose(angle, lk):
    ry, rz = look(lk)
    x, roll = roll_and(angle)
    return sk.merge(roll, {"head": {"r": (0, ry, rz)}, "jaw": {"r": (x, 0, 0)}})


def upper_pose(side):
    def pose(angle):
        return {f"shoulder{side}": {"r": (0, angle, 0)}}
    return pose


def fore_pose(side):
    def pose(angle, hand):
        return sk.merge({f"elbow{side}": {"r": (0, angle, 0)}}, sk.hand(side, sk.SHAPES[int(hand)]))
    return pose


CHANNELS = ["hop", "legs", "lean", "squash", "pitch", "look", "eyes", "jaw",
            "armR", "elbowR", "handR", "armL", "elbowL", "handL", "x", "face", "stride", "skull"]   # skull: pops up (px)


def axis(name, values, sources, labels=None):
    ax = {"name": name, "values": values, "sources": sources}
    if labels:
        ax["labels"] = labels
    return ax


def arm_parts(side):
    return [
        {"name": f"upper{side}", "parent": "body", "joints": [f"shoulder{side}"], "pivot": f"shoulder{side}",
         "anchors": {f"fore{side}": f"elbow{side}"},
         "axes": [axis("angle", UPPER_ANGLES, [f"arm{side}"])], "pose": upper_pose(side)},
        {"name": f"fore{side}", "parent": f"upper{side}",
         "joints": [f"elbow{side}", f"open{side}", f"fist{side}", f"point{side}"], "pivot": f"elbow{side}",
         "tip": f"tip{side}",
         "axes": [axis("angle", FORE_ANGLES, [f"arm{side}", f"elbow{side}"]),
                  axis("hand", HANDS, [f"hand{side}"], ["open", "fist", "point"])],
         "pose": fore_pose(side)},
    ]


PARTS = [
    {"name": "legs", "joints": ["hipR", "hipL", "kneeR", "kneeL"], "pivot": "root", "anchors": {"body": "hips"},
     "axes": [axis("bend", BENDS, ["legs"]), axis("stride", STRIDES, ["stride"])], "pose": legs_pose},
    {"name": "body", "parent": "legs", "joints": ["hips", "neck"], "pivot": "hips",
     "anchors": {"skull": "head", "upperR": "shoulderR", "upperL": "shoulderL"},
     "axes": [axis("lean", LEANS, ["lean"]), axis("shape", list(SHAPES), ["squash"])], "pose": body_pose},
    {"name": "skull", "parent": "body", "joints": ["head", "eyeR", "eyeL"], "pivot": "head", "anchors": {"jaw": "jaw"},
     "lift": ["skull"],
     "axes": [axis("pitch", rng(-104, 64, 4), ["lean", "pitch"]), axis("look", LOOKS, ["look"]),
              axis("eyes", list(EYES), ["eyes"], [v[0] for v in EYES.values()])], "pose": skull_pose},
    {"name": "jaw", "parent": "skull", "joints": ["jaw"], "pivot": "jaw",
     "axes": [axis("angle", rng(-104, 48, 4), ["lean", "pitch", "jaw"]), axis("look", LOOKS, ["look"])],
     "pose": jaw_pose},
    *arm_parts("R"),
    *arm_parts("L"),
]
DRAW_ORDER = ["upperR", "foreR", "legs", "body", "skull", "jaw", "upperL", "foreL"]

if __name__ == "__main__":
    lib.render_parts(sk.build_character, sk.TURN_DEG, PARTS)
    meta = os.path.join(lib.OUT, "parts.json")
    d = json.load(open(meta))
    d["draw_order"] = DRAW_ORDER
    d["channels"] = CHANNELS
    d["ground"] = "legs"
    json.dump(d, open(meta, "w"), indent=1)
