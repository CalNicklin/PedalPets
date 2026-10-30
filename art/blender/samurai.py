"""Samurai hype character (afro, red headband). See lib.py for how to run."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import J, P, action, blob, evaluate, joint, merge, ring  # noqa: E402

lib.COLOURS.update({
    "ink":   ((0.02, 0.02, 0.02), "#181616"),   # kimono, afro, brows (first: line colour)
    "skin":  ((0.45, 0.45, 0.45), "#96928c"),
    "red":   ((0.80, 0.05, 0.05), "#c82020"),
    "white": ((1.00, 1.00, 1.00), "#faf8f2"),
})
lib.KEYED = ("root", "hips", "chest", "shoulderR", "shoulderL", "neck", "head", "eyeR", "eyeL",
         "browR", "browL", "mouth")




def build_character():
    root = J["root"] = joint("root", J["turn"])               # squash/stretch about the feet
    # Legs stay planted; the body bounces on top of them.
    for side in (-1, 1):
        blob(f"leg{side}", "ink", root, (0.17 * side, 0, 0.2), (0.12, 0.12, 0.24))
        blob(f"foot{side}", "ink", root, (0.2 * side, -0.07, 0.05), (0.15, 0.24, 0.07))

    hips = J["hips"] = joint("hips", root, (0, 0, 0.4))
    blob("torso", "ink", hips, (0, 0, 0.28), (0.36, 0.27, 0.38))     # kimono
    blob("sash", "red", hips, (0, 0, 0.1), (0.37, 0.28, 0.06))
    blob("collar", "skin", hips, (0, -0.2, 0.55), (0.13, 0.06, 0.12))  # open neckline

    chest = J["chest"] = joint("chest", hips, (0, 0, 0.5))
    for side, name in ((-1, "R"), (1, "L")):
        sh = J[f"shoulder{name}"] = joint(f"shoulder{name}", chest, (0.36 * side, 0, 0.06))
        sh.rotation_euler = (0, 0, 0)
        blob(f"arm{name}", "ink", sh, (0.04 * side, 0, -0.24), (0.1, 0.1, 0.24), rot=(0, 10 * side, 0))
        J[f"hand{name}"] = hand = joint(f"hand{name}", sh, (0.1 * side, 0, -0.44))
        blob(f"fist{name}", "skin", hand, (0, 0, 0), (0.1, 0.1, 0.1))

    neck = J["neck"] = joint("neck", chest, (0, 0, 0.1))
    head = J["head"] = joint("head", neck, (0, 0, 0.04))
    blob("face", "skin", head, (0, 0, 0.3), (0.32, 0.29, 0.34))
    afro = J["afro"] = joint("afro", head, (0, 0.2, 0.52))
    blob("afro", "ink", afro, (0, 0.05, 0.05), (0.6, 0.42, 0.46), segs=24)
    ring("band", "red", head, (0, 0.0, 0.42), 0.31, 0.045, scale=(1.03, 0.95, 1), rot=(-8, 0, 0))
    # Headband tails trail behind the head (secondary motion).
    for side, name in ((-1, "R"), (1, "L")):
        t1 = J[f"tail{name}1"] = joint(f"tail{name}1", head, (0.2 * side, 0.25, 0.42))
        blob(f"tail{name}a", "red", t1, (0.13 * side, 0.03, -0.05), (0.17, 0.03, 0.05), rot=(0, 20 * side, 0))
        t2 = J[f"tail{name}2"] = joint(f"tail{name}2", t1, (0.3 * side, 0.04, -0.1))
        blob(f"tail{name}b", "red", t2, (0.13 * side, 0.0, -0.04), (0.16, 0.025, 0.045), rot=(0, 25 * side, 0))
    # Face: brows (ink), eyes (white slits), mouth.
    face = J["face"] = joint("face", head, (0, -0.27, 0.3))
    for side, name in ((-1, "R"), (1, "L")):
        eye = J[f"eye{name}"] = joint(f"eye{name}", face, (0.11 * side, 0, 0.01))
        blob(f"eye{name}", "white", eye, (0, 0, 0), (0.075, 0.03, 0.04))
        brow = J[f"brow{name}"] = joint(f"brow{name}", face, (0.12 * side, -0.01, 0.08))
        blob(f"brow{name}", "ink", brow, (0, 0, 0), (0.1, 0.03, 0.025), rot=(0, 14 * side, 0))
    J["mouth"] = mouth = joint("mouth", face, (0, 0, -0.14))
    blob("mouth", "ink", mouth, (0, -0.01, 0), (0.09, 0.03, 0.025))



def arms(r_y, l_y=None, r_x=0, l_x=None):
    """Raise arms in the screen plane (degrees outward-up); right arm is -x."""
    l_y = -r_y if l_y is None else l_y
    l_x = r_x if l_x is None else l_x
    return P(shoulderR={"r": (r_x, r_y, 0)}, shoulderL={"r": (l_x, l_y, 0)})


def eyes(sz, sx=1.0):
    return P(eyeR={"s": (sx, 1, sz)}, eyeL={"s": (sx, 1, sz)})


def brows(up):
    return P(browR={"l": (0, 0, up)}, browL={"l": (0, 0, up)})


def mouth(w, h):
    return P(mouth={"s": (w, 1, h)})


HUB = merge(arms(6), P(mouth={"s": (1.1, 1, 1)}))
ASLEEP = merge(
    P(hips={"l": (0, 0, -0.26), "r": (16, 0, 0)}, chest={"r": (14, 0, 0)},
      head={"r": (26, 0, 6)}, root={"s": (1.04, 1, 0.97)}),
    arms(4, r_x=-18), eyes(0.12), brows(-0.01), mouth(0.6, 1.4))


def stance(**kw):
    return merge(HUB, *kw.values())


# Idle loops: start and end on HUB (Asleep on ASLEEP) so they hand over cleanly.
action("curious", 64, [
    (0, HUB),
    (16, merge(HUB, P(head={"r": (0, 6, 10)}, chest={"r": (0, 2, 0)}, root={"s": (1.012, 1, 0.985)},
                      browL={"l": (0, 0, 0.02)}))),
    (32, merge(HUB, P(head={"r": (-4, 0, 0)}, chest={"r": (-3, 0, 0)}, root={"s": (0.99, 1, 1.015)}))),
    (46, merge(HUB, P(head={"r": (0, -5, -10)}, browR={"l": (0, 0, 0.02)}))),
    (49, merge(HUB, P(head={"r": (0, -5, -10)}), eyes(0.1))),
    (52, merge(HUB, P(head={"r": (0, -4, -8)}))),
    (64, HUB),
], loop=True, idle="Curious")

action("groove", 24, [
    (0, HUB),
    (6, merge(HUB, P(head={"r": (18, 0, 0)}, chest={"r": (6, 0, 0)}, hips={"l": (0, 0, -0.05)},
                     root={"s": (1.04, 1, 0.95)}), arms(6, r_x=16, l_x=-16), mouth(1.2, 1.6))),
    (12, merge(HUB, P(head={"r": (-6, 0, 0)}, hips={"l": (0, 0, 0.02)}, root={"s": (0.98, 1, 1.02)}))),
    (18, merge(HUB, P(head={"r": (4, 0, 0)}), arms(6, r_x=-10, l_x=10))),
    (24, HUB),
], loop=True, idle="IntoIt")

action("hyped", 16, [
    (0, HUB),
    (4, merge(HUB, P(head={"r": (30, 0, 0)}, chest={"r": (10, 0, 0)}, hips={"l": (0, 0, -0.08)},
                     root={"s": (1.07, 1, 0.9)}), arms(100, -20), mouth(1.3, 3), brows(-0.015))),
    (8, merge(HUB, P(head={"r": (-12, 0, 0)}, chest={"r": (-4, 0, 0)}, hips={"l": (0, 0, 0.06)},
                     root={"s": (0.95, 1, 1.07)}), arms(150, -30), mouth(1.4, 3.5))),
    (12, merge(HUB, P(head={"r": (6, 0, 0)}), arms(60, -15), mouth(1.2, 1.8))),
    (16, HUB),
], loop=True, idle="Hyped")

action("asleep", 48, [
    (0, ASLEEP),
    (24, merge(ASLEEP, P(root={"s": (1.02, 1, 1.0)}, head={"r": (30, 0, 6)}), mouth(0.7, 2.2))),
    (48, ASLEEP),
], loop=True, idle="Asleep")

# Reactions: start and end on HUB.
BLOWN = merge(P(hips={"r": (-18, 0, 0), "l": (0, 0, 0.06)}, chest={"r": (-10, 0, 0)},
                head={"r": (-22, 0, 0)}, root={"s": (0.94, 1, 1.08)}),
              arms(130), mouth(1.6, 4.5), eyes(1.8, 1.2), brows(0.05))
action("big_hit", 31, [
    (0, HUB),
    (3, merge(HUB, P(root={"s": (1.04, 1, 0.95)}, head={"r": (8, 0, 0)}), eyes(0.6))),
    (7, BLOWN),
    (16, merge(BLOWN, P(head={"r": (-17, 0, 0)}), arms(120))),
    (23, merge(HUB, P(hips={"r": (6, 0, 0)}, head={"r": (8, 0, 0)}, root={"s": (1.02, 1, 0.97)}))),
    (30, HUB),
], trigger="BigHit", entry_window=4)

BANG_UP = merge(HUB, P(head={"r": (-10, 0, 0)}), arms(40, -70, r_x=10), mouth(1.2, 2))
BANG_DOWN = merge(HUB, P(head={"r": (38, 0, 0)}, chest={"r": (14, 0, 0)}, hips={"l": (0, 0, -0.06)},
                         root={"s": (1.06, 1, 0.9)}), arms(55, -60, r_x=-10), mouth(1.4, 3.5), brows(-0.02))
action("flurry", 22, [
    (0, HUB), (3, BANG_UP), (6, BANG_DOWN), (9, BANG_UP), (12, BANG_DOWN), (15, BANG_UP), (21, HUB),
], trigger="Flurry", loop_from=3, loop_len=12, entry_window=9)

AWE = merge(HUB, P(hips={"r": (8, 0, 0)}, head={"r": (-8, 0, 0)}), arms(150, r_x=-15),
            eyes(1.7, 1.15), mouth(1.0, 3.2), brows(0.045))
action("sustain", 39, [
    (0, HUB),
    (10, AWE),
    (18, merge(AWE, P(head={"r": (-8, 6, 4)}, root={"s": (1.0, 1, 1.02)}))),
    (26, AWE),
    (38, HUB),
], trigger="Sustain", loop_from=10, loop_len=16, loop_until="SustainEnd", loop_max=6000,
   entry_window=6)

CROUCH = merge(HUB, P(hips={"l": (0, 0, -0.18), "r": (10, 0, 0)}, root={"s": (1.08, 1, 0.86)},
                      head={"r": (-6, 0, 0)}), arms(30, r_x=30), eyes(0.7), brows(-0.03), mouth(0.8, 1))
action("swell", 39, [
    (0, HUB),
    (12, CROUCH),
    (16, merge(CROUCH, P(root={"s": (1.09, 1, 0.84)}, hips={"l": (0, 0, -0.19), "r": (10, 0, 0)}))),
    (20, CROUCH),
    (24, merge(HUB, P(hips={"l": (0, 0, 0.32)}, root={"s": (0.9, 1, 1.12)}, head={"r": (-10, 0, 0)}),
               arms(160), eyes(1.6), mouth(1.5, 4))),
    (28, merge(HUB, P(hips={"l": (0, 0, 0.36)}), arms(150), eyes(1.4), mouth(1.4, 3))),
    (32, merge(HUB, P(hips={"l": (0, 0, -0.1)}, root={"s": (1.1, 1, 0.88)}), arms(40))),
    (38, HUB),
], trigger="Swell", loop_from=12, loop_len=8, loop_until="SwellPeak", loop_max=5000,
   entry_window=6)

POINT = merge(HUB, P(chest={"r": (0, 0, -8)}, head={"r": (-4, 0, -6)}), arms(75, r_x=-35),
              mouth(1.5, 1.6), brows(0.02))
action("cut", 21, [
    (0, HUB), (4, POINT), (14, merge(POINT, P(head={"r": (-2, 0, -4)}))), (20, HUB),
], trigger="Cut", freeze_ms=450)

action("wake", 29, [
    (0, ASLEEP),
    (3, merge(HUB, P(hips={"l": (0, 0, 0.15)}, root={"s": (0.9, 1, 1.12)}), arms(60), eyes(1.8, 1.2),
              brows(0.05), mouth(1.2, 3))),
    (8, merge(HUB, eyes(1.5, 1.1), brows(0.03))),
    (13, merge(HUB, P(head={"r": (0, 0, 25)}), eyes(1.2))),
    (20, merge(HUB, P(head={"r": (0, 0, -25)}), eyes(1.2))),
    (28, HUB),
], trigger="Wake", start=ASLEEP)

action("drift_off", 33, [
    (0, HUB),
    (10, merge(HUB, P(root={"s": (0.96, 1, 1.06)}, head={"r": (-12, 0, 0)}), arms(160), eyes(0.1),
               mouth(1.3, 5))),
    (18, merge(HUB, P(head={"r": (8, 0, 0)}), arms(10), eyes(0.4), mouth(0.8, 1.4))),
    (32, ASLEEP),
], trigger="DriftOff", entry_window=6)



def bounce(pose):
    """Vertical position of the head, roughly (body height + squash)."""
    return pose["hips"]["l"][2] + 1.3 * (pose["root"]["s"][2] - 1) - 0.004 * pose["head"]["r"][0]


def secondary(act, f):
    """Tails and afro follow the head's vertical motion with a lag."""
    def vel(t, lag):
        return (bounce(evaluate(act, t - lag)) - bounce(evaluate(act, t - lag - 1))) * 30

    v1, v2 = vel(f, 2), vel(f, 4)
    droop = -18
    a1 = max(-60, min(50, droop - 260 * v1))
    a2 = max(-50, min(50, -8 - 300 * v2))
    afro = max(-0.1, min(0.1, -1.5 * vel(f, 1)))
    return {
        "tailR1": {"r": (0, a1, 0)}, "tailL1": {"r": (0, -a1, 0)},
        "tailR2": {"r": (0, a2, 0)}, "tailL2": {"r": (0, -a2, 0)},
        "afro": {"s": (1 + afro, 1, 1 - afro)},
    }



lib.run(build_character, secondary, turn_deg=-22)
