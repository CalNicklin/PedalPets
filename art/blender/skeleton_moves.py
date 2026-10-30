"""The skeleton's movement vocabulary for the paper-doll choreographer.

Pure Python (no Blender): tools/build_moves.py turns this into
src/gen/chars/skeleton/. Channels and units (see skeleton_doll.py):
  hop px · legs -1 tuck (airborne)/0 stand/1 crouch/2 low · stride -1..1 · lean° (+forward)
  squash -1 stretch/0/1/2 squash · pitch° (+down) · look° (45 = at you) · eyes -1 wide/0/1 half/2 closed
  jaw° (+open) · armR/armL° (0 hanging, + toward the way he faces, 180 up) · elbowR/elbowL° (same sense)
  handR/handL 0 open/1 fist (grips)/2 point · x px travel (+ forward) · skull px (pops up)
  lean past -24 rolls the body back across the picture: -90 lies flat (legs 3)

R is the far arm (on the side he faces), L the near one: "up and out" is
armR +150, armL -150. Moves start and end at 0 so they blend into anything.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from moves_lib import MARK_IMAGES, cycle, new_registry, path, planted_travel  # noqa: E402,F401

MOVES, move = new_registry()


def arms(r=None, l=None):
    """Arm channel keys: r/l are dicts like {"arm": keys, "elbow": keys, "hand": keys}."""
    out = {}
    for side, spec in (("R", r), ("L", l)):
        for k, v in (spec or {}).items():
            out[f"{k}{side}"] = v
    return out


LEG_PX = 21.5          # hip to sole in pixels (skeleton.py THIGH + SHIN at 44.8 px per unit)
STRIDE_DEG = 26       # leg swing at stride 1 (skeleton.legs_pose)


def walk_keys(frames, steps, size=0.4):
    """Walk with planted feet: travel comes from the leg swing itself (see
    moves_lib.planted_travel). Arms swing against the legs, a nod and a lean
    each step."""
    step = frames / steps
    stride = [(0, 0)] + [(round(step * (i + 0.5)), size if i % 2 == 0 else -size) for i in range(steps)] + [(frames, 0)]
    swing = [(f, -40 * v) for f, v in stride]
    nod = [(0, 0)]
    for i in range(steps):
        nod += [(round(step * (i + 0.5)), 4), (round(step * (i + 1)), 0)]
    return {"stride": stride, "x": planted_travel(stride, frames, LEG_PX, STRIDE_DEG), "pitch": nod,
            "armR": swing, "armL": [(f, -v) for f, v in swing], "lean": [(0, 0), (4, 5), (frames - 4, 5), (frames, 0)]}


def hop_keys(frames, up, height, land):
    """Crouch, spring up, tuck, land and absorb."""
    crouch = [(up - 2, 1)] if up > 2 else []
    return {"hop": [(0, 0), (up, 0), (up + 4, height), (land - 4, height * 0.8), (land, 0), (frames, 0)],
            "legs": [(0, 0), *crouch, (up, 1), (up + 2, -1), (land - 2, -1), (land, 1), (land + 4, 0.6), (frames, 0)],
            "squash": [(0, 0), (up, 1), (up + 3, -1), (land, 1), (land + 4, 0.5), (frames, 0)]}


# --- idle: little things a skeleton does while listening -------------------------
move("look_l", 44, look=[(0, 0), (6, -30), (36, -28), (44, 0)], pitch=[(0, 0), (6, 6), (36, 6), (44, 0)])
move("look_r", 44, look=[(0, 0), (6, 30), (36, 28), (44, 0)], pitch=[(0, 0), (6, -4), (36, -4), (44, 0)])
move("tilt", 40, look=[(0, 0), (6, 15), (32, 15), (40, 0)], pitch=[(0, 0), (6, -10), (32, -8), (40, 0)])
move("blink", 5, eyes=[(0, 0), (1, 2), (3, 2), (4, 0), (5, 0)])
move("double_blink", 11, eyes=[(0, 0), (1, 2), (2, 2), (3, 0), (6, 0), (7, 2), (8, 2), (9, 0), (11, 0)])
move("chatter", 20, jaw=cycle(20, 4, [14, 0], start=2, end=18))
move("scratch", 56, **arms(l={"arm": [(0, 0), (10, -168), (46, -168), (56, 0)],
                              "elbow": [(0, 0), (10, -150)] + [(14 + 4 * i, -150 + (16 if i % 2 == 0 else 0)) for i in range(8)]
                              + [(46, -150), (56, 0)]}),
     look=[(0, 0), (10, 15), (46, 15), (56, 0)], pitch=[(0, 0), (10, 10), (46, 10), (56, 0)])
# Impatient knee bounce, a hand on the hip.
move("tap_foot", 40, legs=cycle(40, 10, [0.4, 0], start=4, end=36), pitch=cycle(40, 10, [5, 0], start=4, end=36),
     lean=[(0, 0), (6, -4), (34, -4), (40, 0)],
     **arms(r={"arm": [(0, 0), (8, 20), (32, 20), (40, 0)], "elbow": [(0, 0), (8, 70), (32, 70), (40, 0)]}))
move("knuckles", 36, **arms(r={"arm": [(0, 0), (8, 60), (28, 60), (36, 0)], "elbow": [(0, 0), (8, 60), (28, 60), (36, 0)],
                               "hand": [(0, 0), (8, 1), (28, 1), (36, 0)]},
                            l={"arm": [(0, 0), (8, 50), (28, 50), (36, 0)], "elbow": [(0, 0), (8, 70), (28, 70), (36, 0)],
                               "hand": [(0, 0), (8, 1), (28, 1), (36, 0)]}),
     squash=[(0, 0), (12, 0.5), (16, 0), (20, 0.5), (24, 0), (36, 0)], jaw=[(0, 0), (14, 8), (22, 0), (36, 0)])
move("stretch", 52, **arms(r={"arm": [(0, 0), (14, 165), (38, 165), (52, 0)]}, l={"arm": [(0, 0), (14, -165), (38, -165), (52, 0)]}),
     squash=[(0, 0), (14, -1), (38, -1), (52, 0)], jaw=[(0, 0), (14, 40), (34, 40), (44, 0), (52, 0)],
     eyes=[(0, 0), (14, 1), (34, 2), (44, 0), (52, 0)], pitch=[(0, 0), (14, -16), (38, -16), (52, 0)])
move("hop_small", 22, **hop_keys(22, 4, 6, 14))
move("walk", 40, **walk_keys(40, 4))
move("walk_long", 64, **walk_keys(64, 6), look=[(0, 0), (20, 0), (30, 15), (46, 15), (58, 0), (64, 0)])
move("turn_round", 20, flip_at=8, hop=[(0, 0), (3, 0), (8, 6), (13, 0), (20, 0)],
     legs=[(0, 0), (2, 0.75), (6, -1), (10, -1), (13, 0.6), (20, 0)], squash=[(0, 0), (2, 0.75), (8, -0.5), (13, 0.6), (20, 0)],
     **arms(r={"arm": [(0, 0), (7, 40), (13, 0)]}, l={"arm": [(0, 0), (7, -40), (13, 0)]}))
move("inspect", 44, lean=[(0, 0), (10, 22), (34, 22), (44, 0)], pitch=[(0, 0), (10, 30), (34, 30), (44, 0)],
     legs=[(0, 0), (10, 1), (34, 1), (44, 0)],
     **arms(r={"arm": [(0, 0), (10, 30), (34, 30), (44, 0)], "elbow": [(0, 0), (10, 10), (18, 30), (22, 10), (26, 30), (34, 10), (44, 0)],
               "hand": [(0, 0), (10, 2), (34, 2), (44, 0)]}))
# Waves with the far arm, up on the open side: looking at you turns the skull
# toward the near arm, which would put the hand in front of his face.
move("wave", 48, look=[(0, 0), (6, 45), (42, 45), (48, 0)],
     **arms(r={"arm": [(0, 0), (8, 150), (40, 150), (48, 0)],
               "elbow": [(0, 0), (8, 20)] + [(12 + 4 * i, 55 if i % 2 == 0 else 15) for i in range(7)] + [(40, 20), (48, 0)]}))
move("beckon", 44, look=[(0, 0), (6, 45), (38, 45), (44, 0)],
     **arms(r={"arm": [(0, 0), (8, 70), (36, 70), (44, 0)],
               "elbow": [(0, 0), (8, 30)] + [(12 + 6 * i, 110 if i % 2 == 0 else 40) for i in range(4)] + [(36, 30), (44, 0)],
               "hand": [(0, 0), (8, 2), (36, 2), (44, 0)]}))
move("shrug", 36, squash=[(0, 0), (8, -0.5), (26, -0.5), (36, 0)], look=[(0, 0), (8, 30), (26, 30), (36, 0)],
     pitch=[(0, 0), (8, -6), (26, -6), (36, 0)],
     **arms(r={"arm": [(0, 0), (8, 40), (26, 40), (36, 0)], "elbow": [(0, 0), (8, 80), (26, 80), (36, 0)]},
            l={"arm": [(0, 0), (8, -40), (26, -40), (36, 0)], "elbow": [(0, 0), (8, -80), (26, -80), (36, 0)]}))
move("shake", 26, look=[(0, 0), (4, 18), (8, -18), (12, 18), (16, -12), (22, 0), (26, 0)],
     jaw=[(0, 0), (4, 8), (12, 0), (16, 8), (26, 0)])
move("shade_eyes", 56, **arms(r={"arm": [(0, 0), (10, 128), (46, 128), (56, 0)], "elbow": [(0, 0), (10, 95), (46, 95), (56, 0)]}),
     pitch=[(0, 0), (10, -4), (46, -4), (56, 0)], lean=[(0, 0), (10, 6), (46, 6), (56, 0)])

# Lie back, hands behind the skull, a hum, a glance at you; then get up.
move("lie_back", 240, solo=True, legs=[(0, 0), (14, 1.5), (26, 2.4), (36, 3), (200, 3), (214, 2.4), (226, 1.2), (240, 0)],
     lean=[(0, 0), (14, -8), (26, -40), (36, -90), (200, -90), (214, -40), (226, -6), (240, 0)],
     look=[(0, 0), (110, 0), (118, 45), (150, 45), (158, 0), (240, 0)],
     pitch=[(0, 0), (26, 0), (40, 18), (196, 18), (214, 0), (240, 0)],     # head up on its hands, off the ground
     jaw=[(0, 0), (60, 0)] + [(64 + 6 * i, 8 if i % 2 == 0 else 0) for i in range(8)] + [(120, 0), (240, 0)],
     **arms(r={"arm": [(0, 0), (30, 0), (46, -105), (190, -105), (206, 0), (240, 0)],
               "elbow": [(0, 0), (30, 0), (46, -120), (190, -120), (206, 0), (240, 0)]},
            l={"arm": [(0, 0), (30, 0), (46, -135), (190, -135), (206, 0), (240, 0)],
               "elbow": [(0, 0), (30, 0), (46, -105), (190, -105), (206, 0), (240, 0)]}))
move("sit", 150, solo=True, legs=[(0, 0), (16, 2), (28, 2.5), (130, 2.5), (140, 1.5), (150, 0)],
     lean=[(0, 0), (16, 8), (28, -20), (130, -20), (140, 6), (150, 0)],
     pitch=[(0, 0), (28, 8), (130, 8), (150, 0)],
     **arms(r={"arm": [(0, 0), (24, 35), (130, 35), (150, 0)], "elbow": [(0, 0), (24, 60), (130, 60), (150, 0)]},
            l={"arm": [(0, 0), (24, 25), (130, 25), (150, 0)], "elbow": [(0, 0), (24, 70), (130, 70), (150, 0)]}))
# Bend down and brush the leaves about with the far hand.
move("sweep", 52, legs=[(0, 0), (10, 1.5), (42, 1.5), (52, 0)], lean=[(0, 0), (10, 30), (42, 30), (52, 0)],
     pitch=[(0, 0), (10, 26), (42, 26), (52, 0)],
     **arms(r={"arm": [(0, 0), (10, 10), (16, 60), (22, 5), (28, 60), (34, 5), (40, 50), (46, 10), (52, 0)],
               "elbow": [(0, 0), (10, 10), (46, 10), (52, 0)]}))
# The Mind's approach (a couple of steps) and reach (pick it up, have a look, toss it).
move("step", 16, **walk_keys(16, 1))
move("pick_up", 100, solo=True, legs=[(0, 0), (12, 2), (22, 2), (34, 0), (100, 0)],
     lean=[(0, 0), (12, 34), (22, 34), (34, 0), (66, 0), (72, -6), (80, 8), (100, 0)],
     pitch=[(0, 0), (12, 26), (22, 26), (34, -4), (64, -4), (100, 0)],
     look=[(0, 0), (44, 0), (50, 15), (58, 15), (64, 0), (100, 0)],
     **arms(r={"arm": [(0, 0), (12, 6), (22, 6), (34, 112), (64, 112), (72, 50), (78, 165), (86, 130), (100, 0)],
               "elbow": [(0, 0), (12, 0), (22, 0), (34, 118), (64, 118), (72, 140), (78, 0), (100, 0)],
               "hand": [(0, 0), (16, 0), (18, 1), (77, 1), (79, 0), (100, 0)]}))
# A big bored sigh: breathe in (stretch up), let it all out (slump), a shake of the skull.
move("sigh", 50, squash=[(0, 0), (12, -1), (20, -1), (30, 1), (44, 0.5), (50, 0)],
     pitch=[(0, 0), (12, -10), (20, -10), (30, 16), (44, 10), (50, 0)],
     jaw=[(0, 0), (12, 12), (20, 12), (28, 4), (50, 0)], look=[(0, 0), (32, 0), (36, 12), (40, -12), (44, 0), (50, 0)],
     **arms(r={"arm": [(0, 0), (12, 12), (30, -4), (50, 0)]}, l={"arm": [(0, 0), (12, -12), (30, 4), (50, 0)]}))
# Asleep: slumped, the odd jaw twitch.
move("breathe", 60, lean=[(0, 0), (30, 3), (60, 0)], pitch=[(0, 0), (30, 4), (60, 0)], jaw=[(0, 0), (30, 4), (60, 0)])
move("twitch", 14, jaw=[(0, 0), (3, 12), (7, 0), (14, 0)], **arms(l={"elbow": [(0, 0), (4, -20), (14, 0)]}))

# --- the groove: a bar of two beats, looped in time with the music ------------------
# Sampled by the beat clock's phase (0 = on the beat), so frame counts are just
# resolution (16 per beat). A bounce, not a wave: knees dip just after each
# beat and ease back up; the head nods a couple of frames behind; the head
# sways and the arms swing across the bar.
def bounce(depth, at=3, back=11, frames=32, beats=2):
    """A dip on every beat of the bar: down by `at` frames into the beat, eased back up by `back`."""
    per = frames // beats
    keys = [(0, 0)]
    for b in range(beats):
        keys += [(b * per + at, depth), (b * per + back, depth * 0.08), ((b + 1) * per, 0)]
    return keys


move("groove", 32, legs=bounce(0.8), squash=bounce(0.55), pitch=bounce(14, 5, 13), jaw=bounce(8, 4, 10),
     look=[(0, 0), (8, 10), (16, 0), (24, -10), (32, 0)],
     **arms(r={"arm": [(0, 0), (8, 14), (16, 0), (24, -6), (32, 0)], "elbow": bounce(10, 4, 12)},
            l={"arm": [(0, 0), (8, 6), (16, 0), (24, -14), (32, 0)], "elbow": bounce(-10, 4, 12)}))
move("groove_hyped", 32, legs=bounce(0.9), squash=bounce(0.7), pitch=bounce(22, 4, 12), lean=bounce(7, 4, 12),
     jaw=bounce(14, 4, 11), look=[(0, 0), (8, 8), (16, 0), (24, -8), (32, 0)],
     **arms(r={"arm": bounce(18, 4, 12), "elbow": bounce(25, 4, 12)}, l={"arm": bounce(-18, 4, 12), "elbow": bounce(-25, 4, 12)}))

# --- groove: beat moves --------------------------------------------------------
move("nod", 14, pitch=[(0, 0), (4, 16), (9, -4), (14, 0)], jaw=[(0, 0), (4, 10), (9, 0), (14, 0)],
     squash=[(0, 0), (4, 0.5), (14, 0)])
move("bob", 16, lean=[(0, 0), (4, 8), (10, -3), (16, 0)], legs=[(0, 0), (4, 0.5), (10, 0), (16, 0)],
     pitch=[(0, 0), (4, 8), (16, 0)])
move("side_nod", 14, pitch=[(0, 0), (4, 12), (14, 0)], look=[(0, 0), (4, 15), (14, 0)])
move("snap", 16, **arms(r={"arm": [(0, 0), (4, 60), (12, 60), (16, 0)], "elbow": [(0, 0), (4, 70), (12, 70), (16, 0)],
                           "hand": [(0, 0), (4, 1), (6, 0), (12, 0), (16, 0)]}),
     pitch=[(0, 0), (6, 10), (16, 0)], jaw=[(0, 0), (6, 8), (16, 0)])
move("strum", 16, twos=True, legs=[(0, 0), (4, 0.5), (12, 0.5), (16, 0)], pitch=[(0, 0), (6, 14), (16, 0)],
     **arms(r={"arm": [(0, 0), (4, 70), (12, 70), (16, 0)], "elbow": [(0, 0), (4, 40), (12, 40), (16, 0)],
               "hand": [(0, 0), (4, 1), (12, 1), (16, 0)]},
            l={"arm": [(0, 0), (4, 40), (7, 15), (12, 20), (16, 0)], "elbow": [(0, 0), (4, 100), (7, 70), (12, 80), (16, 0)],
               "hand": [(0, 0), (4, 1), (12, 1), (16, 0)]}))
move("fist_pump", 22, twos=True, squash=[(0, 0), (6, 1), (10, -0.5), (22, 0)], jaw=[(0, 0), (8, 20), (22, 0)],
     **arms(r={"arm": [(0, 0), (6, 110), (10, 160), (16, 140), (22, 0)], "elbow": [(0, 0), (6, 60), (10, 0), (22, 0)],
               "hand": [(0, 0), (3, 1), (18, 1), (22, 0)]}))
move("shimmy", 24, lean=cycle(24, 8, [8, -8], end=22), squash=cycle(24, 8, [0.5, 0], end=22),
     **arms(r={"arm": [(0, 0), (4, 40), (20, 40), (24, 0)], "elbow": [(0, 0), (4, 60), (20, 60), (24, 0)]},
            l={"arm": [(0, 0), (4, -40), (20, -40), (24, 0)], "elbow": [(0, 0), (4, -60), (20, -60), (24, 0)]}))
move("hop_beat", 16, hop=[(0, 0), (2, 0), (6, 6), (10, 0), (16, 0)], legs=[(0, 0), (2, 0.75), (4, -1), (9, -1), (10, 0.6), (16, 0)],
     squash=[(0, 0), (2, 0.75), (5, -0.75), (10, 0.6), (16, 0)], jaw=[(0, 0), (6, 12), (12, 0), (16, 0)])
move("strut", 20, **walk_keys(20, 2, 0.5))

# --- hyped: the guitar god ---------------------------------------------------------
# Hyped: big but human-paced. Headbangs ~1.7 Hz, a strum every 12 frames, real
# wind-ups and follow-through; on twos so each pose lands on the slow panel.
move("headbang", 18, twos=True, pitch=[(0, 0), (6, 26), (12, -8), (18, 0)], lean=[(0, 0), (6, 10), (14, 0), (18, 0)],
     jaw=[(0, 0), (6, 24), (14, 0), (18, 0)], squash=[(0, 0), (6, 0.75), (14, 0), (18, 0)])
move("windmill", 40, twos=True, lean=[(0, 0), (12, -10), (16, -10), (22, 12), (32, 6), (40, 0)],
     jaw=[(0, 0), (16, 10), (22, 32), (34, 10), (40, 0)], legs=[(0, 0), (12, 0.25), (22, 1), (34, 0.5), (40, 0)],
     pitch=[(0, 0), (12, -14), (16, -14), (22, 18), (34, 6), (40, 0)],
     **arms(r={"arm": [(0, 0), (6, 70), (34, 70), (40, 0)], "elbow": [(0, 0), (6, 40), (34, 40), (40, 0)],
               "hand": [(0, 0), (6, 1), (34, 1), (40, 0)]},
            l={"arm": [(0, 0), (12, -170), (16, -172), (22, 40), (28, 24), (34, 20), (40, 0)],
               "elbow": [(0, 0), (12, -10), (22, 20), (34, 10), (40, 0)], "hand": [(0, 0), (6, 1), (34, 1), (40, 0)]}))
move("cheer_jump", 36, twos=True, **hop_keys(36, 6, 16, 24), jaw=[(0, 0), (8, 34), (22, 28), (32, 0), (36, 0)],
     eyes=[(0, 0), (8, -1), (22, -1), (28, 0), (36, 0)],
     **arms(r={"arm": [(0, 0), (6, 20), (12, 150), (22, 145), (32, 0), (36, 0)], "hand": [(0, 0), (10, 1), (24, 1), (32, 0), (36, 0)]},
            l={"arm": [(0, 0), (6, -20), (12, -150), (22, -145), (32, 0), (36, 0)], "hand": [(0, 0), (10, 1), (24, 1), (32, 0), (36, 0)]}))
move("pogo", 54, twos=True,
     hop=[(0, 0), (3, 0), (9, 12), (15, 0), (18, 0), (24, 13), (30, 0), (33, 0), (39, 12), (45, 0), (54, 0)],
     legs=[(0, 0), (3, 1), (5, -1), (13, -1), (15, 1), (18, 1), (20, -1), (28, -1), (30, 1), (33, 1), (35, -1),
           (43, -1), (45, 1), (49, 0.5), (54, 0)],
     squash=[(0, 0), (3, 1), (6, -1), (15, 1), (18, 1), (21, -1), (30, 1), (33, 1), (36, -1), (45, 1), (49, 0.5), (54, 0)],
     pitch=[(0, 0), (9, -16), (15, 10), (24, -16), (30, 10), (39, -16), (45, 10), (54, 0)],
     jaw=[(0, 0), (9, 26), (45, 26), (54, 0)],
     **arms(r={"arm": [(0, 0), (9, 150), (15, 100), (24, 150), (30, 100), (39, 150), (45, 100), (54, 0)],
               "hand": [(0, 0), (6, 1), (48, 1), (54, 0)]}))
move("shred", 48, twos=True, pitch=cycle(48, 24, [18, -2], end=44), jaw=[(0, 0), (6, 22), (42, 22), (48, 0)],
     legs=[(0, 0), (6, 0.75), (42, 0.75), (48, 0)], lean=cycle(48, 24, [10, 4], end=44),
     **arms(r={"arm": [(0, 0), (6, 75), (42, 75), (48, 0)], "elbow": [(0, 0), (6, 35), (42, 35), (48, 0)],
               "hand": [(0, 0), (6, 1), (42, 1), (48, 0)]},
            l={"arm": cycle(48, 12, [40, 14], start=4, end=44), "elbow": cycle(48, 12, [95, 70], start=4, end=44),
               "hand": [(0, 0), (4, 1), (44, 1), (48, 0)]}))
move("hop_travel", 22, twos=True, **hop_keys(22, 2, 12, 14), x=[(0, 0), (2, 0), (14, 12), (22, 12)],
     **arms(r={"arm": [(0, 0), (6, 120), (14, 60), (22, 0)]}, l={"arm": [(0, 0), (6, -120), (14, -60), (22, 0)]}))
move("turn_hop", 22, twos=True, flip_at=8, **hop_keys(22, 2, 12, 14),
     **arms(r={"arm": [(0, 0), (6, 90), (14, 30), (22, 0)]}, l={"arm": [(0, 0), (6, -90), (14, -30), (22, 0)]}))

# --- reactions -----------------------------------------------------------------
move("startle", 30, twos=True, x=[(0, 0), (2, 0), (8, -6), (14, -8), (30, -8)],
     lean=[(0, 0), (6, -14), (16, -10), (24, 4), (30, 0)], hop=[(0, 0), (2, 0), (6, 9), (13, 0), (30, 0)],
     legs=[(0, 0), (2, 1), (5, -1), (11, -1), (14, 0.9), (18, 0.7), (24, 0)],
     squash=[(0, 0), (2, 1), (6, -1), (14, 1), (18, 0.7), (24, 0)], eyes=[(0, 0), (3, -1), (20, -1), (26, 0)],
     jaw=[(0, 0), (5, 44), (18, 30), (28, 0)], pitch=[(0, 0), (6, -14), (18, -8), (30, 0)],
     skull=[(0, 0), (3, 0), (7, 10), (10, 13), (14, 3), (16, 0), (18, 2), (20, 0), (30, 0)],   # pops off and drops back
     **arms(r={"arm": [(0, 0), (6, 150), (16, 130), (28, 0)], "elbow": [(0, 0), (6, 20), (28, 0)]},
            l={"arm": [(0, 0), (6, -150), (16, -130), (28, 0)], "elbow": [(0, 0), (6, -20), (28, 0)]}))
move("flutter", 28, twos=True, loop=(4, 16), jaw=[(0, 0), (4, 24), (20, 24), (27, 0)], legs=[(0, 0), (4, 0.75), (20, 0.75), (27, 0)],
     **arms(r={"arm": [(0, 0), (4, 80), (20, 80), (27, 0)], "elbow": [(0, 0), (4, 30), (20, 30), (27, 0)],
               "hand": [(0, 0), (4, 1), (20, 1), (27, 0)]},
            l={"arm": [(0, 0)] + [(4 + 2 * i, 45 if i % 2 == 0 else 15) for i in range(9)] + [(27, 0)],
               "elbow": [(0, 0), (4, 100), (20, 100), (27, 0)], "hand": [(0, 0), (4, 1), (20, 1), (27, 0)]}))
move("sing", 40, loop=(10, 16), loop_until="SustainEnd", loop_max=6000,
     pitch=[(0, 0), (10, -26), (18, -28), (26, -26), (39, 0)], jaw=[(0, 0), (10, 44), (26, 44), (39, 0)],
     eyes=[(0, 0), (10, 1), (26, 1), (39, 0)], look=[(0, 0), (10, 0), (18, 8), (26, 0), (39, 0)],
     **arms(r={"arm": [(0, 0), (10, 100), (26, 100), (39, 0)], "elbow": [(0, 0), (10, 20), (26, 20), (39, 0)]},
            l={"arm": [(0, 0), (10, -100), (26, -100), (39, 0)], "elbow": [(0, 0), (10, -20), (26, -20), (39, 0)]}))
move("launch", 48, loop=(12, 8), loop_until="SwellPeak", loop_max=5000,
     legs=[(0, 0), (12, 2), (20, 2), (23, -1), (34, -1), (37, 1), (48, 0)],
     squash=[(0, 0), (12, 2), (20, 2), (25, -1), (31, 0), (38, 2), (48, 0)],
     lean=[(0, 0), (12, 16), (20, 16), (26, 0), (48, 0)], eyes=[(0, 0), (12, 1), (20, 1), (25, -1), (40, 0)],
     jaw=[(0, 0), (20, 0), (26, 40), (40, 0)], hop=[(0, 0), (20, 0), (26, 22), (30, 25), (34, 22), (38, 0), (48, 0)],
     **arms(r={"arm": [(0, 0), (12, -30), (20, -30), (26, 160), (36, 150), (44, 0), (48, 0)], "hand": [(0, 0), (24, 1), (40, 1), (48, 0)]},
            l={"arm": [(0, 0), (12, 30), (20, 30), (26, -160), (36, -150), (44, 0), (48, 0)], "hand": [(0, 0), (24, 1), (40, 1), (48, 0)]}))
move("point", 24, freeze_ms=450, jaw=[(0, 0), (4, 10), (18, 10), (24, 0)], pitch=[(0, 0), (4, -6), (18, -6), (24, 0)],
     **arms(r={"arm": [(0, 0), (4, 90), (18, 88), (24, 0)], "hand": [(0, 0), (3, 2), (20, 2), (24, 0)]}))
move("wake", 32, eyes=[(0, 0), (2, -1), (10, -1), (16, 0), (32, 0)], squash=[(0, 0), (3, -1), (8, 0.5), (14, 0), (32, 0)],
     look=[(0, 0), (12, 0), (16, 30), (22, -30), (28, 0), (32, 0)], jaw=[(0, 0), (3, 20), (10, 0), (32, 0)],
     **arms(r={"arm": [(0, 0), (3, 60), (12, 0), (32, 0)]}, l={"arm": [(0, 0), (3, -60), (12, 0), (32, 0)]}))
move("yawn", 40, jaw=[(0, 0), (10, 46), (26, 46), (36, 0), (40, 0)], eyes=[(0, 0), (10, 1), (30, 2), (36, 1), (40, 0)],
     pitch=[(0, 0), (10, -18), (26, -18), (40, 0)],
     **arms(r={"arm": [(0, 0), (10, 60), (26, 60), (38, 0), (40, 0)]}, l={"arm": [(0, 0), (10, -60), (26, -60), (38, 0), (40, 0)]}))

STANCES = {
    "Asleep":  {"legs": 3, "lean": -90, "pitch": 16, "eyes": 2, "jaw": 8, "armR": 70, "armL": 60, "elbowR": 40, "elbowL": 50},
    "Curious": {"armR": 6, "armL": -6, "elbowR": 10, "elbowL": -10},
    "IntoIt":  {"lean": 4, "legs": 0.25, "armR": 14, "armL": -10, "elbowR": 30, "elbowL": -20, "handR": 1, "handL": 1},
    "Hyped":   {"lean": 6, "legs": 0.5, "jaw": 12, "armR": 24, "armL": -20, "elbowR": 50, "elbowL": -40, "handR": 1, "handL": 1},
}

VOCAB = {
    "Asleep":  [("breathe", 6, "idle"), ("twitch", 1, "idle")],
    "Curious": [("look_l", 3, "idle"), ("look_r", 3, "idle"), ("tilt", 2, "idle"), ("blink", 4, "idle"),
                ("double_blink", 1, "idle"), ("chatter", 1, "idle"), ("scratch", 2, "idle"), ("hop_small", 2, "idle"),
                ("walk", 6, "idle"), ("walk_long", 4, "idle"), ("step", 2, "idle"), ("turn_round", 4, "idle"),
                ("inspect", 2, "idle"), ("sweep", 1, "idle")],
    "IntoIt":  [("snap", 3, "beat"), ("strum", 4, "beat"), ("fist_pump", 2, "beat"), ("shimmy", 2, "beat"),
                ("hop_beat", 1, "beat"), ("strut", 3, "beat"), ("side_nod", 1, "beat"),
                ("blink", 3, "idle"), ("chatter", 1, "idle"), ("turn_round", 1, "idle")],
    "Hyped":   [("shred", 5, "beat"), ("windmill", 4, "beat"), ("headbang", 3, "beat"), ("cheer_jump", 3, "beat"),
                ("pogo", 2, "beat"), ("fist_pump", 2, "beat"), ("hop_travel", 1, "beat"), ("turn_hop", 1, "beat"),
                ("blink", 1, "idle")],
}
IDLE_GAPS = {"Asleep": (1800, 4500), "Curious": (500, 1600), "IntoIt": (1200, 3000), "Hyped": (1200, 3000)}
BEAT_MS = {"Asleep": 0, "Curious": 0, "IntoIt": 560, "Hyped": 500}
GROOVES = {"IntoIt": ("groove", 2), "Hyped": ("groove_hyped", 2)}   # (move, beats it spans)

INTENTS = {
    "Watch":       {"vocab": [("shade_eyes", 3), ("blink", 2), ("tilt", 1)], "gap": (700, 1600)},
    # Bored stops exploring: it slumps where it is and fidgets, slowly.
    "Bored":       {"vocab": [("sigh", 3), ("tap_foot", 2), ("knuckles", 1), ("lie_back", 3), ("sit", 3),
                              ("shrug", 1), ("stretch", 1), ("yawn", 1), ("chatter", 1), ("double_blink", 1)],
                    "gap": (1800, 4000),
                    "stance": {"pitch": 14, "eyes": 1, "lean": 6, "squash": 0.5, "jaw": 6,
                               "armR": -4, "armL": 4, "elbowR": -8, "elbowL": 8, "look": -15}},
    "WantsYou":    {"vocab": [("wave", 4), ("beckon", 3), ("shrug", 2), ("hop_small", 1)], "gap": (600, 1400),
                    "stance": {"pitch": -6, "squash": -0.5, "lean": -4}},   # perks up
    "Investigate": {"vocab": [("blink", 2), ("tilt", 1)], "gap": (600, 1400)},   # the Mind asks for step / pick_up
}
TURN_MOVE = "turn_round"
ROLES = {"head": "skull", "gust": "armL", "hands": [("foreR", "handR"), ("foreL", "handL")],
         "approach": "step", "reach": "pick_up", "reach_px": 15}

REACTIONS = {
    "BigHit": ["startle"], "Flurry": ["flutter"], "Sustain": ["sing"], "Swell": ["launch"], "Cut": ["point"],
    "Wake": ["wake"], "DriftOff": ["yawn"],
}

# --- expression marks ------------------------------------------------------------
MARK_COLOURS = {"#": "ink", "n": "socket", "s": "glow", "w": "bone", "b": "bow", "g": "shade"}
# Offsets: skull pivot (the neck) -> mark's top-left, facing screen-left (+dx is behind).
MARKS = {
    "bang": [("bang_s", 6, -36)] * 2 + path("bang", 16, (6, -40), (6, -42)) + [("bang_s", 6, -38)] * 2,
    "question": path("question", 24, (10, -40), (10, -42)),
    "notes": path("note", 30, (-16, -22), (-26, -46), sway=2),
    "zzz": path("z_small", 22, (10, -26), (16, -38)) + path("z_big", 26, (16, -42), (24, -56), sway=1, sway_period=26),
    "sweat": path("drop", 14, (14, -20), (24, -6)),
}
MOVE_MARKS = {
    "startle": ("bang", 2), "tilt": ("question", 8), "scratch": ("question", 14), "sing": ("notes", 10),
    "breathe": ("zzz", 10), "flutter": ("sweat", 4), "launch": ("bang", 26), "lie_back": ("notes", 66),
}
