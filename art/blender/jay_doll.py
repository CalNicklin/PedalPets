"""Blue jay as a paper doll: each body part rendered on its own over its pose
range, with 2D attachment points. See docs/superpowers/specs/2026-10-30-paper-doll-design.md.

  /Applications/Blender.app/Contents/MacOS/Blender -b -P art/blender/jay_doll.py -- <out_dir> [part ...]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jay  # noqa: E402  (character geometry and pose helpers)
import lib  # noqa: E402

HIP = 0.34          # standing hip height (world units)


def rng(lo, hi, step):
    return [lo + i * step for i in range(int(round((hi - lo) / step)) + 1)]


# Discrete-looking axes are numbered so every channel is a number the device
# can add up; the nearest value picks the image. Squash and leg bend step in
# quarters (about a pixel each) so crouches and squashes move smoothly.
def lerp_table(keys, step):
    """{value: (label, scale)} at every `step`, interpolating the key scales."""
    out = {}
    ks = sorted(keys)
    v = ks[0]
    while v <= ks[-1] + 1e-9:
        lo = max(k for k in ks if k <= v + 1e-9)
        hi = min(k for k in ks if k >= v - 1e-9)
        u = 0 if hi == lo else (v - lo) / (hi - lo)
        a, b = keys[lo][1], keys[hi][1]
        out[round(v, 2)] = (f"{keys[lo][0]}+{u:.2f}" if u else keys[lo][0],
                            tuple(x + (y - x) * u for x, y in zip(a, b)))
        v += step
    return out


SHAPES = lerp_table({      # squash channel -> body scale x, y, z
    -1: ("stretch", (0.95, 1.0, 1.06)),
    0:  ("normal",  (1.0, 1.0, 1.0)),
    1:  ("squash",  (1.05, 1.0, 0.93)),
    2:  ("big",     (1.1, 1.0, 0.86)),
}, 0.25)
SHAPES[3] = ("fluff", (1.12, 1.1, 0.92))
LEGS = lerp_table({        # legs channel -> hip height, leg length scale, feet lift
    0: ("stand",  (HIP, 1.0, 0.0)),
    1: ("crouch", (0.27, 0.27 / HIP, 0.0)),
    2: ("low",    (0.21, 0.21 / HIP, 0.0)),
}, 0.25)
LEGS[-1] = ("tuck", (HIP, 0.6, 0.12))   # airborne: below stand so crouch -> stand -> tuck rises steadily
LEGS = dict(sorted(LEGS.items()))
EYES = {            # eyes channel -> eye scale x, z
    -1: ("wide",   (1.15, 1.5)),
    0:  ("open",   (1.0, 1.0)),
    1:  ("half",   (1.0, 0.45)),
    2:  ("closed", (1.0, 0.1)),
}
LOOKS = rng(-30, 45, 15)        # 45 turns the head round toward the viewer
LEANS = rng(-24, 24, 3)        # body lean: 3° keeps the neck moving <= ~1 px per step
WING_LEANS = [-16, -8, 0, 8, 16]


def look(l):
    """Head look: turn plus a matching tilt (the tilt tops out at 30° so looking
    out at the viewer stays a curious tilt, not a sideways head)."""
    return (0.7 * max(-30, min(30, l)), l)


def legs_pose(v):
    h, s, lift = LEGS[v][1]
    return {"legs": {"l": (0, 0, h - HIP), "s": (1, 1, s)}, "feet": {"l": (0, 0, lift)}}


def body_pose(lean, shape):
    return {"hips": {"r": (lean, 0, 0), "s": SHAPES[shape][1]}}


def head_pose(pitch, lk, eyes):
    ry, rz = look(lk)
    sx, sz = EYES[eyes][1]
    return {"head": {"r": (pitch, ry, rz)},
            "eyeR": {"s": (sx, 1, sz)}, "eyeL": {"s": (sx, 1, sz)}}


def crest_pose(angle, lk):
    ry, rz = look(lk)
    return {"head": {"r": (0, ry, rz)}, "crest": {"r": (angle, 0, 0)}}


def jaw_pose(angle, lk):
    ry, rz = look(lk)
    return {"head": {"r": (0, ry, rz)}, "jaw": {"r": (angle, 0, 0)}}


def tail_pose(angle):
    return {"tail": {"r": (angle, 0, 0)}}


def wing_pose(side):
    def pose(flap, lean):
        w = jay.wings(flap)[f"shoulder{side}"]
        return {"hips": {"r": (lean, 0, 0)}, f"shoulder{side}": w}
    return pose


# Channels the device animates (tools/build_doll.py turns these into an enum).
CHANNELS = ["hop", "legs", "lean", "squash", "pitch", "look", "eyes", "jaw", "crest", "tail",
            "flapL", "flapR", "x", "face"]   # x: stage position (px); face: < 0 mirrored


def axis(name, values, sources, labels=None):
    """An image axis; its value on the device is the sum of `sources` channels."""
    ax = {"name": name, "values": values, "sources": sources}
    if labels:
        ax["labels"] = labels
    return ax


PARTS = [
    {"name": "legs", "joints": ["legs", "feet"], "pivot": "root", "anchors": {"body": "legs"},
     "axes": [axis("bend", list(LEGS), ["legs"], [v[0] for v in LEGS.values()])], "pose": legs_pose},
    {"name": "body", "parent": "legs", "joints": ["hips"], "pivot": "hips",
     "anchors": {"head": "head", "wingR": "shoulderR", "wingL": "shoulderL", "tail": "tail"},
     "axes": [axis("lean", LEANS, ["lean"]),
              axis("shape", list(SHAPES), ["squash"], [v[0] for v in SHAPES.values()])],
     "pose": body_pose},
    {"name": "head", "parent": "body", "joints": ["neck", "head", "eyeR", "eyeL"], "pivot": "head",
     "anchors": {"crest": "crest", "jaw": "jaw"},
     "axes": [axis("pitch", rng(-36, 64, 4), ["lean", "pitch"]), axis("look", LOOKS, ["look"]),
              axis("eyes", list(EYES), ["eyes"], [v[0] for v in EYES.values()])],
     "pose": head_pose},
    {"name": "crest", "parent": "head", "joints": ["crest"], "pivot": "crest",
     "axes": [axis("angle", rng(-80, 80, 8), ["lean", "pitch", "crest"]), axis("look", LOOKS, ["look"])],
     "pose": crest_pose},
    {"name": "jaw", "parent": "head", "joints": ["jaw"], "pivot": "jaw",
     "axes": [axis("angle", rng(-40, 80, 8), ["lean", "pitch", "jaw"]), axis("look", LOOKS, ["look"])],
     "pose": jaw_pose},
    {"name": "tail", "parent": "body", "joints": ["tail"], "pivot": "tail",
     "axes": [axis("angle", rng(-48, 48, 8), ["lean", "tail"])], "pose": tail_pose},
    {"name": "wingR", "parent": "body", "joints": ["shoulderR"], "pivot": "shoulderR",
     "axes": [axis("flap", rng(0, 165, 11), ["flapR"]), axis("lean", WING_LEANS, ["lean"])],
     "pose": wing_pose("R")},
    {"name": "wingL", "parent": "body", "joints": ["shoulderL"], "pivot": "shoulderL",
     "axes": [axis("flap", rng(0, 165, 11), ["flapL"]), axis("lean", WING_LEANS, ["lean"])],
     "pose": wing_pose("L")},
]
DRAW_ORDER = ["wingR", "tail", "legs", "body", "crest", "head", "jaw", "wingL"]

lib.render_parts(jay.build_character, jay.TURN_DEG, PARTS)
import json  # noqa: E402
_meta = os.path.join(lib.OUT, "parts.json")
_d = json.load(open(_meta))
_d["draw_order"] = DRAW_ORDER
_d["channels"] = CHANNELS
_d["ground"] = "legs"
json.dump(_d, open(_meta, "w"), indent=1)
