"""Blue jay: crest, flapping wings, bobbing tail. See lib.py for how to run."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import J, P, action, blob, cone, evaluate, joint, merge, ring  # noqa: E402

lib.COLOURS.update({
    "ink":   ((0.02, 0.02, 0.02), "#181616"),   # beak, necklace, bars, pupils (line colour)
    "blue":  ((0.04, 0.17, 0.66), "#3b6fd4"),   # back, head, crest, wings, tail
    "navy":  ((0.02, 0.06, 0.30), "#28479a"),   # wings, tail
    "sky":   ((0.25, 0.50, 0.88), "#8cbaf0"),   # wing coverts
    "white": ((1.00, 1.00, 1.00), "#faf8f2"),   # face, belly, wing patches
    "grey":  ((0.30, 0.29, 0.27), "#9a948c"),   # legs, belly shade
})
lib.KEYED = ("root", "hips", "tail", "shoulderR", "shoulderL", "neck", "head", "crest", "jaw",
             "eyeR", "eyeL")


def build_character():
    root = J["root"] = joint("root", J["turn"])
    # Legs hang from the hip: scaling `legs` in z shortens them (crouch/tuck).
    legs = J["legs"] = joint("legs", root, (0, 0, 0.34))
    for side in (-1, 1):
        cone(f"leg{side}", "grey", legs, (0.11 * side, 0.02, -0.17), 0.035, 0.03, 0.34)
    feet = J["feet"] = joint("feet", root, (0, 0, 0))
    for side in (-1, 1):
        blob(f"foot{side}", "grey", feet, (0.11 * side, -0.06, 0.02), (0.07, 0.13, 0.03))

    hips = J["hips"] = joint("hips", root, (0, 0, 0.34))
    blob("body", "blue", hips, (0, 0.05, 0.42), (0.4, 0.46, 0.48), rot=(-12, 0, 0))
    blob("belly", "white", hips, (0, -0.16, 0.32), (0.32, 0.3, 0.36))
    blob("shade", "grey", hips, (0, -0.1, 0.12), (0.26, 0.26, 0.14))

    tail = J["tail"] = joint("tail", hips, (0, 0.38, 0.28))
    # Tail points back and down along d = (0, cos 32°, -sin 32°).
    def along(k):
        return (0, 0.848 * k, -0.53 * k)
    blob("tail", "navy", tail, along(0.42), (0.17, 0.5, 0.06), rot=(-32, 0, 0))
    blob("tailbar", "ink", tail, along(0.74), (0.15, 0.06, 0.07), rot=(-32, 0, 0))
    blob("tailtip", "white", tail, along(0.86), (0.13, 0.05, 0.065), rot=(-32, 0, 0))

    for side, name in ((-1, "R"), (1, "L")):
        sh = J[f"shoulder{name}"] = joint(f"shoulder{name}", hips, (0.33 * side, 0.02, 0.62))
        blob(f"wing{name}", "navy", sh, (0.04 * side, 0.12, -0.24), (0.07, 0.24, 0.34), rot=(-18, 0, 0))
        blob(f"covert{name}", "sky", sh, (0.06 * side, 0.02, -0.1), (0.06, 0.15, 0.14), rot=(-18, 0, 0))
        blob(f"bar{name}", "ink", sh, (0.06 * side, 0.15, -0.36), (0.05, 0.16, 0.035), rot=(-18, 0, 0))
        blob(f"patch{name}", "white", sh, (0.06 * side, 0.2, -0.47), (0.045, 0.1, 0.05), rot=(-18, 0, 0))

    neck = J["neck"] = joint("neck", hips, (0, -0.08, 0.78))
    ring("necklace", "ink", neck, (0, -0.02, 0.06), 0.2, 0.03, scale=(1, 0.95, 1), rot=(-10, 0, 0))
    head = J["head"] = joint("head", neck, (0, 0, 0.08))
    blob("skull", "blue", head, (0, 0.02, 0.22), (0.27, 0.28, 0.26))
    blob("cheeks", "white", head, (0, -0.12, 0.12), (0.22, 0.17, 0.16))
    crest = J["crest"] = joint("crest", head, (0, 0.08, 0.38))
    cone("crest", "blue", crest, (0, 0.07, 0.14), 0.13, 0.0, 0.42, rot=(-30, 0, 0))
    for side, name in ((-1, "R"), (1, "L")):
        eye = J[f"eye{name}"] = joint(f"eye{name}", head, (0.2 * side, -0.17, 0.27))
        blob(f"eyering{name}", "white", eye, (0, 0, 0), (0.08, 0.06, 0.08))
        blob(f"pupil{name}", "ink", eye, (0.03 * side, -0.03, 0.005), (0.05, 0.04, 0.055))
    cone("beak", "ink", head, (0, -0.42, 0.17), 0.085, 0.0, 0.3, scale=(1, 1, 0.75), rot=(90, 0, 0))
    jaw = J["jaw"] = joint("jaw", head, (0, -0.28, 0.12))
    cone("jaw", "ink", jaw, (0, -0.1, -0.005), 0.06, 0.0, 0.22, scale=(1, 1, 0.55), rot=(95, 0, 0))


# --- poses ---------------------------------------------------------------------

def wings(r_y, l_y=None, r_x=0, l_x=None):
    """Raise wings out and up (degrees; ~160 = a V above the back); right wing
    is -x. Raised wings fan out wider so they read as wings, not arms."""
    l_y = -r_y if l_y is None else l_y
    l_x = r_x if l_x is None else l_x

    def fan(a):
        k = max(0.0, min(1.0, abs(a) / 150))
        return (1, 1 + 0.45 * k, 1 + 0.2 * k)
    return P(shoulderR={"r": (r_x, r_y, 0), "s": fan(r_y)}, shoulderL={"r": (l_x, l_y, 0), "s": fan(l_y)})


def eyes(sz, sx=1.0):
    return P(eyeR={"s": (sx, 1, sz)}, eyeL={"s": (sx, 1, sz)})


def crest(angle):
    """+ flattens the crest back (calm), - raises it (excited)."""
    return P(crest={"r": (angle, 0, 0)})


def beak(open_deg):
    return P(jaw={"r": (open_deg, 0, 0)})


HUB = merge(wings(3))
ASLEEP = merge(
    P(hips={"s": (1.12, 1.1, 0.92), "r": (6, 0, 0)}, neck={"l": (0, 0.04, -0.12)},
      head={"r": (22, 0, 8)}, tail={"r": (12, 0, 0)}),
    wings(1), eyes(0.1), crest(45))


def show():
    lib.ACTIONS.clear()
    action("hub", 1, [(0, HUB)])


# Idle loops: start and end on HUB (Asleep on ASLEEP) so they hand over cleanly.
action("curious", 64, [
    (0, HUB),
    (8, merge(HUB, P(head={"r": (0, 18, 14)}))),
    (20, merge(HUB, P(head={"r": (0, 20, 16)}), crest(-12))),
    (26, merge(HUB, P(head={"r": (0, 2, 0)}, tail={"r": (-8, 0, 0)}))),
    (36, merge(HUB, P(head={"r": (0, -16, -20)}))),
    (46, merge(HUB, P(head={"r": (0, -18, -22)}), crest(-6))),
    (49, merge(HUB, P(head={"r": (0, -18, -22)}), eyes(0.1))),
    (52, merge(HUB, P(head={"r": (0, -14, -18)}))),
    (64, HUB),
], loop=True, idle="Curious")

action("groove", 24, [
    (0, HUB),
    (6, merge(HUB, P(neck={"l": (0, -0.08, -0.03)}, head={"r": (14, 0, 0)}, hips={"r": (6, 0, 0)},
                     root={"s": (1.04, 1, 0.95)}, tail={"r": (-7, 0, 0)}), wings(12), crest(-10))),
    (12, merge(HUB, P(neck={"l": (0, 0.03, 0.02)}, head={"r": (-6, 0, 0)}, root={"s": (0.98, 1, 1.02)},
                      tail={"r": (3, 0, 0)}))),
    (18, merge(HUB, P(neck={"l": (0, -0.03, 0)}, head={"r": (4, 0, 0)}), wings(8))),
    (24, HUB),
], loop=True, idle="IntoIt")

def hyped_keys():
    """Peak state: a full wing beat every 8 frames (240 ms, ~4 Hz; faster
    smears into a blur on the LCD), two big hops per loop, body rocking
    forward/back with the head banging against it."""
    import math
    keys = []
    for k in range(0, 33, 2):
        hop = math.sin(math.pi * (k % 16) / 16)           # 0 on the ground, 1 at the top
        land = 1 - hop                                     # squash on landing
        rock = math.sin(2 * math.pi * k / 32)
        wing = 95 - 70 * math.cos(2 * math.pi * k / 8)     # 25 (down) .. 165 (high V)
        pose = merge(HUB, P(
            hips={"r": (14 * rock, 0, 0)},
            root={"l": (0, 0, 0.3 * hop), "s": (1 + 0.09 * land, 1, 1 - 0.13 * land)},
            head={"r": (-16 * rock + 10 * land, 0, 0)},
            tail={"r": (-10 * rock, 0, 0)}),
            wings(wing), crest(-40), beak(24 + 8 * hop))
        keys.append((k, pose))
    keys[-1] = (32, keys[0][1])                            # seamless loop
    return keys


action("hyped", 32, hyped_keys(), loop=True, idle="Hyped")

action("asleep", 48, [
    (0, ASLEEP),
    (24, merge(ASLEEP, P(hips={"s": (1.15, 1.12, 0.94), "r": (6, 0, 0)}, head={"r": (25, 0, 8)}))),
    (48, ASLEEP),
], loop=True, idle="Asleep")

# Reactions: start and end on HUB.
STARTLED = merge(P(hips={"r": (-14, 0, 0)}, root={"l": (0, 0, 0.12), "s": (0.93, 1, 1.08)},
                   head={"r": (-14, 0, 0)}, tail={"r": (-20, 0, 0)}),
                 wings(150), crest(-40), beak(28), eyes(1.6, 1.2))
action("big_hit", 31, [
    (0, HUB),
    (3, merge(HUB, P(root={"s": (1.05, 1, 0.94)}), eyes(0.6))),
    (7, STARTLED),
    (16, merge(STARTLED, P(head={"r": (-10, 0, 0)}), wings(135))),
    (23, merge(HUB, P(hips={"r": (5, 0, 0)}, root={"s": (1.02, 1, 0.97)}), crest(-12))),
    (30, HUB),
], trigger="BigHit", entry_window=4)

FLAP_UP = merge(HUB, P(root={"l": (0, 0, 0.06), "s": (0.97, 1, 1.03)}, tail={"r": (4, 0, 0)}),
                wings(160), crest(-30), beak(14))
FLAP_DOWN = merge(HUB, P(root={"l": (0, 0, 0.0), "s": (1.05, 1, 0.94)}, tail={"r": (-5, 0, 0)}),
                  wings(40), crest(-24), beak(20))
action("flurry", 27, [
    (0, HUB), (4, FLAP_UP), (8, FLAP_DOWN), (12, FLAP_UP), (16, FLAP_DOWN), (20, FLAP_UP), (26, HUB),
], trigger="Flurry", loop_from=4, loop_len=16, entry_window=13)

SING = merge(HUB, P(neck={"l": (0, 0.02, 0.06)}, head={"r": (-24, 0, 0)}, root={"s": (0.97, 1, 1.04)}),
             wings(28), crest(-36), beak(34), eyes(0.5))
action("sustain", 39, [
    (0, HUB),
    (10, SING),
    (18, merge(SING, P(head={"r": (-26, 8, 6)}), wings(34))),
    (26, SING),
    (38, HUB),
], trigger="Sustain", loop_from=10, loop_len=16, loop_until="SustainEnd", loop_max=6000,
   entry_window=6)

CROUCH = merge(HUB, P(root={"s": (1.1, 1, 0.85)}, hips={"r": (14, 0, 0)}, head={"r": (-8, 0, 0)},
                      tail={"r": (-18, 0, 0)}), wings(18, r_x=20), crest(20), eyes(0.7))
action("swell", 39, [
    (0, HUB),
    (12, CROUCH),
    (16, merge(CROUCH, P(root={"s": (1.12, 1, 0.83)}))),
    (20, CROUCH),
    (24, merge(HUB, P(root={"l": (0, 0, 0.42), "s": (0.9, 1, 1.12)}, tail={"r": (16, 0, 0)}),
               wings(160), crest(-40), beak(22), eyes(1.4))),
    (28, merge(HUB, P(root={"l": (0, 0, 0.5)}), wings(40), crest(-36), beak(18))),
    (32, merge(HUB, P(root={"s": (1.1, 1, 0.88)}), wings(70))),
    (38, HUB),
], trigger="Swell", loop_from=12, loop_len=8, loop_until="SwellPeak", loop_max=5000,
   entry_window=6)

POINT = merge(HUB, P(hips={"r": (0, 0, -6)}, head={"r": (-6, 0, -10)}),
              wings(80, 3, r_x=-40), crest(-30), beak(12))
action("cut", 21, [
    (0, HUB), (4, POINT), (14, merge(POINT, P(head={"r": (-4, 0, -6)}))), (20, HUB),
], trigger="Cut", freeze_ms=450)

action("wake", 29, [
    (0, ASLEEP),
    (3, merge(HUB, P(root={"l": (0, 0, 0.1), "s": (0.92, 1, 1.1)}), wings(60), crest(-40),
              eyes(1.6, 1.2), beak(14))),
    (8, merge(HUB, crest(-20), eyes(1.3, 1.1))),
    (13, merge(HUB, P(head={"r": (0, 0, 30)}), crest(-10))),
    (20, merge(HUB, P(head={"r": (0, 0, -30)}), crest(-10))),
    (28, HUB),
], trigger="Wake")

action("drift_off", 33, [
    (0, HUB),
    (10, merge(HUB, P(head={"r": (-16, 0, 0)}, root={"s": (0.96, 1, 1.05)}), wings(100), eyes(0.1),
               beak(36), crest(-10))),
    (18, merge(HUB, P(head={"r": (8, 0, 0)}), wings(6), eyes(0.4), crest(20))),
    (32, ASLEEP),
], trigger="DriftOff", entry_window=6)


# --- follow-through ------------------------------------------------------------

def bounce(pose):
    return pose["root"]["l"][2] + pose["hips"]["l"][2] + 1.2 * (pose["root"]["s"][2] - 1)


def secondary(act, f):
    """Tail and crest lag behind the body's vertical motion and the head's nod."""
    def vel(fn, t, lag):
        return (fn(evaluate(act, t - lag)) - fn(evaluate(act, t - lag - 1))) * 30

    keyed = evaluate(act, f)
    v_body = vel(bounce, f, 2)
    v_nod = vel(lambda p: p["head"]["r"][0], f, 2) / 30
    tail = max(-10, min(10, -70 * v_body))
    crest_lag = max(-20, min(20, 0.8 * v_nod * 30 / 10))
    t = keyed["tail"]["r"]
    c = keyed["crest"]["r"]
    return {"tail": {"r": (t[0] + tail, t[1], t[2])},
            "crest": {"r": (c[0] + crest_lag, c[1], c[2])}}


TURN_DEG = -48

if __name__ == "__main__":
    if os.environ.get("PET_HUB_ONLY"):
        show()
    lib.run(build_character, secondary, turn_deg=TURN_DEG)
