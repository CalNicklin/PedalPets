"""A cute little skeleton: big skull, glowing pupils, clacking jaw, bony arms
that can point, wave and play air guitar. See lib.py for how to run; this
file renders a few full-body preview poses (skeleton_doll.py renders parts).

  /Applications/Blender.app/Contents/MacOS/Blender -b -P art/blender/skeleton.py -- <out_dir>

Arms move in the screen plane: each shoulder and elbow joint is turned back
to face the camera, so rotating about its local Y swings the bone across the
picture (0 = hanging down, + = forward/toward the way he faces, 180 = up).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import J, P, action, blob, cone, joint, merge  # noqa: E402

lib.COLOURS.update({
    "ink":    ((0.02, 0.02, 0.03), "#1c1820"),   # outlines, nose, teeth gaps
    "bone":   ((0.86, 0.80, 0.66), "#f2ead6"),   # bones
    "shade":  ((0.48, 0.42, 0.33), "#bdb094"),   # bone shade, far side
    "socket": ((0.05, 0.03, 0.08), "#3b2f4a"),   # eye sockets, rib gaps
    "glow":   ((0.30, 0.95, 0.75), "#7ff0d0"),   # pupils
    "bow":    ((0.62, 0.06, 0.05), "#d2463c"),   # bow tie
})

TURN_DEG = -32
HIP = 0.50                 # hip height standing
THIGH, SHIN = 0.24, 0.24
UPPER, FORE = 0.28, 0.25   # arm bones (long enough to reach past the skull)
SHOULDER_Z = 0.97

lib.KEYED = ("root", "legs", "hipR", "hipL", "kneeR", "kneeL", "hips", "neck", "head", "jaw",
             "eyeR", "eyeL", "shoulderR", "shoulderL", "elbowR", "elbowL",
             "openR", "openL", "fistR", "fistL", "pointR", "pointL")


def bone(name, mat, parent, top, length, r=0.032, knob=0.048):
    """A long bone hanging down from `top` (in its parent's frame), knobs at both ends."""
    x, y, z = top
    cone(name, mat, parent, (x, y, z - length / 2), r, r * 0.9, length)
    blob(name + "_k1", mat, parent, (x, y, z), (knob, knob, knob))
    blob(name + "_k2", mat, parent, (x, y, z - length), (knob * 0.9, knob * 0.9, knob * 0.9))


def screen_joint(name, parent, loc):
    """A joint whose local axes face the camera (rotating about Y swings it in the picture)."""
    j = joint(name, parent, loc)
    j.rotation_euler = (0, 0, math.radians(-TURN_DEG))
    return j


def build_hand(side, name, wrist):
    """Three hand shapes, each on its own joint so a pose shows one (scale 1) and hides the others."""
    open_ = J[f"open{name}"] = joint(f"open{name}", wrist)
    blob(f"palm{name}", "bone", open_, (0, 0, -0.035), (0.045, 0.03, 0.045))
    for i, a in enumerate((-28, 0, 28)):
        fx = math.sin(math.radians(a)) * 0.05
        fz = -0.06 - math.cos(math.radians(a)) * 0.035
        cone(f"finger{name}{i}", "bone", open_, (fx, 0, fz), 0.014, 0.012, 0.06, rot=(0, a, 0))
    fist = J[f"fist{name}"] = joint(f"fist{name}", wrist)
    blob(f"fistball{name}", "bone", fist, (0, 0, -0.045), (0.05, 0.04, 0.05))
    point = J[f"point{name}"] = joint(f"point{name}", wrist)
    blob(f"pointball{name}", "bone", point, (0, 0, -0.04), (0.045, 0.035, 0.045))
    cone(f"pointer{name}", "bone", point, (0, 0, -0.1), 0.015, 0.012, 0.09)


def build_character():
    root = J["root"] = joint("root", J["turn"])

    # Legs: thigh and shin per side; `legs` (the hip line) drops for crouches.
    legs = J["legs"] = joint("legs", root, (0, 0, HIP))
    for side, name in ((-1, "R"), (1, "L")):
        mat = "shade" if name == "R" else "bone"
        hip = J[f"hip{name}"] = joint(f"hip{name}", legs, (0.085 * side, 0, 0))
        bone(f"thigh{name}", mat, hip, (0, 0, 0), THIGH, r=0.034)
        knee = J[f"knee{name}"] = joint(f"knee{name}", hip, (0, 0, -THIGH))
        bone(f"shin{name}", mat, knee, (0, 0, 0), SHIN, r=0.03)
        blob(f"foot{name}", mat, knee, (0, -0.05, -SHIN - 0.02), (0.06, 0.1, 0.035))

    # Body: pelvis, spine, ribcage (gaps are dark slits), a bow tie.
    hips = J["hips"] = joint("hips", root, (0, 0, HIP))
    blob("pelvis", "bone", hips, (0, 0, 0.04), (0.15, 0.09, 0.07))
    blob("sacrum", "shade", hips, (0, 0.03, 0.0), (0.05, 0.05, 0.06))
    for i, z in enumerate((0.13, 0.19, 0.25)):
        blob(f"vert{i}", "bone", hips, (0, 0.02, z), (0.04, 0.04, 0.03))
    blob("ribs", "bone", hips, (0, 0, 0.39), (0.19, 0.14, 0.16))
    for i, z in enumerate((0.33, 0.40, 0.47)):
        blob(f"gap{i}", "socket", hips, (0, -0.075, z), (0.13 - 0.01 * i, 0.08, 0.012))
    blob("sternum", "bone", hips, (0, -0.14, 0.40), (0.03, 0.02, 0.12))
    neck = J["neck"] = joint("neck", hips, (0, -0.01, 0.55))
    blob("neck1", "bone", neck, (0, 0, 0.0), (0.04, 0.04, 0.03))
    blob("neck2", "bone", neck, (0, 0, 0.05), (0.038, 0.038, 0.03))
    blob("bowknot", "bow", neck, (0, -0.06, -0.01), (0.03, 0.025, 0.03))
    for side in (-1, 1):
        cone(f"bow{side}", "bow", neck, (0.055 * side, -0.06, -0.01), 0.045, 0.0, 0.09,
             scale=(1, 0.5, 0.9), rot=(0, 90 * side, 0))

    # Skull: big cranium, face, sockets with glowing pupils, nose, upper teeth.
    head = J["head"] = joint("head", neck, (0, 0, 0.08))
    blob("cranium", "bone", head, (0, 0.02, 0.28), (0.31, 0.28, 0.29))
    blob("face", "bone", head, (0, -0.1, 0.17), (0.25, 0.2, 0.17))
    for side, name in ((-1, "R"), (1, "L")):
        blob(f"socket{name}", "socket", head, (0.115 * side, -0.24, 0.27), (0.085, 0.05, 0.09))
        eye = J[f"eye{name}"] = joint(f"eye{name}", head, (0.115 * side, -0.29, 0.26))
        blob(f"pupil{name}", "glow", eye, (0, 0, 0), (0.03, 0.02, 0.034))
    cone("nose", "ink", head, (0, -0.28, 0.165), 0.035, 0.0, 0.05, rot=(180, 0, 0))
    blob("upperteeth", "bone", head, (0, -0.2, 0.07), (0.16, 0.1, 0.05))
    for i, x in enumerate((-0.07, -0.025, 0.025, 0.07)):
        blob(f"utooth{i}", "ink", head, (x, -0.29, 0.065), (0.005, 0.02, 0.03))
    jaw = J["jaw"] = joint("jaw", head, (0, 0.0, 0.07))
    blob("mandible", "bone", jaw, (0, -0.17, -0.04), (0.16, 0.1, 0.05))
    blob("chin", "bone", jaw, (0, -0.22, -0.06), (0.09, 0.05, 0.04))
    for i, x in enumerate((-0.06, -0.02, 0.02, 0.06)):
        blob(f"ltooth{i}", "ink", jaw, (x, -0.26, -0.02), (0.005, 0.02, 0.026))

    # Arms: shoulder and elbow face the camera; hand at the wrist.
    for side, name in ((-1, "R"), (1, "L")):
        mat = "shade" if name == "R" else "bone"
        sh = J[f"shoulder{name}"] = screen_joint(f"shoulder{name}", hips, (0.22 * side, 0, SHOULDER_Z - HIP))
        bone(f"upper{name}", mat, sh, (0, 0, 0), UPPER, r=0.028, knob=0.042)
        el = J[f"elbow{name}"] = joint(f"elbow{name}", sh, (0, 0, -UPPER))
        bone(f"fore{name}", mat, el, (0, 0, 0), FORE, r=0.024, knob=0.036)
        wrist = joint(f"wrist{name}", el, (0, 0, -FORE - 0.01))
        J[f"wrist{name}"] = wrist
        build_hand(side, name, wrist)


# --- poses -------------------------------------------------------------------

HIDE = (0.01, 0.01, 0.01)
SHAPES = ("open", "fist", "point")


def hand(name, shape):
    return {f"{s}{name}": {"s": (1, 1, 1) if s == shape else HIDE} for s in SHAPES}


def arm(name, angle, elbow=0, shape="open"):
    """angle: 0 hanging, + forward (toward the way he faces), 180 straight up; elbow bends the same way."""
    return merge({f"shoulder{name}": {"r": (0, angle, 0)}, f"elbow{name}": {"r": (0, elbow, 0)}}, hand(name, shape))


def legs_pose(bend, stride=0):
    """bend 0 stand .. 2 low (knees forward, hips drop, feet stay put); -1 tucked (airborne)."""
    if bend < 0:
        thigh, knee, drop = 55, -95, 0.0
    else:
        thigh = 32 * bend
        knee = -2 * thigh
        h = (THIGH + SHIN) * math.cos(math.radians(thigh))
        drop = h - (THIGH + SHIN)
    a = 26 * stride
    return {"legs": {"l": (0, 0, drop)},
            "hipR": {"r": (-thigh + a, 0, 0)}, "kneeR": {"r": (-knee, 0, 0)},
            "hipL": {"r": (-thigh - a, 0, 0)}, "kneeL": {"r": (-knee, 0, 0)},
            "hips": {"l": (0, 0, drop)}}


REST = merge(arm("R", 8), arm("L", 8), legs_pose(0))


def show():
    """Preview poses. The near arm is L (screen-right); + angles swing forward
    (screen-left, the way he faces), so the near arm reaches up-and-out with -."""
    lib.ACTIONS.clear()
    action("rest", 1, [(0, REST)])
    action("wave", 1, [(0, merge(REST, arm("L", -150, -30, "open"), P(head={"r": (-6, 0, -8)})))])
    action("point", 1, [(0, merge(REST, arm("L", 95, 0, "point"), P(head={"r": (0, 0, 10)})))])
    action("guitar", 1, [(0, merge(REST, arm("R", 70, 40, "fist"), arm("L", 25, 80, "fist"),
                                   legs_pose(0.5), P(head={"r": (16, 0, 0)}, jaw={"r": (16, 0, 0)})))])
    action("cheer", 1, [(0, merge(REST, arm("R", 150, 10, "fist"), arm("L", -150, -10, "fist"),
                                  P(jaw={"r": (24, 0, 0)}, head={"r": (-14, 0, 0)})))])
    action("crouch", 1, [(0, merge(REST, legs_pose(1.5), arm("R", 30, 40), arm("L", 30, 40)))])
    action("walk", 1, [(0, merge(REST, legs_pose(0, 1), arm("R", -25), arm("L", 25)))])
    action("scratch", 1, [(0, merge(REST, arm("L", -170, -150, "open"), P(head={"r": (8, 0, 12)})))])


def secondary(act, f):
    return {}


if __name__ == "__main__":
    show()
    lib.run(build_character, secondary, turn_deg=TURN_DEG)
