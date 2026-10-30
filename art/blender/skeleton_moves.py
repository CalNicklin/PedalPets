"""The skeleton's movement vocabulary for the paper-doll choreographer.

Pure Python (no Blender): tools/build_moves.py turns this into
src/gen/chars/skeleton/. Channels and units (see skeleton_doll.py):
  hop px · legs -1 tuck (airborne)/0 stand/1 crouch/2 low · stride -1..1 · lean° (+forward)
  squash -1 stretch/0/1/2 squash · pitch° (+down) · look° (45 = at you) · eyes -1 wide/0/1 half/2 closed
  jaw° (+open) · armR/armL° (0 hanging, + toward the way he faces, 180 up) · elbowR/elbowL° (same sense)
  handR/handL 0 open/1 fist/2 point · x px travel (+ forward)

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

# Asleep: slumped, the odd jaw twitch.
move("breathe", 60, lean=[(0, 0), (30, 3), (60, 0)], pitch=[(0, 0), (30, 4), (60, 0)], jaw=[(0, 0), (30, 4), (60, 0)])
move("twitch", 14, jaw=[(0, 0), (3, 12), (7, 0), (14, 0)], **arms(l={"elbow": [(0, 0), (4, -20), (14, 0)]}))

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
move("fist_pump", 16, twos=True, squash=[(0, 0), (4, 1), (8, -0.5), (16, 0)], jaw=[(0, 0), (6, 20), (16, 0)],
     **arms(r={"arm": [(0, 0), (4, 110), (8, 165), (12, 140), (16, 0)], "elbow": [(0, 0), (4, 60), (8, 0), (16, 0)],
               "hand": [(0, 0), (2, 1), (14, 1), (16, 0)]}))
move("shimmy", 24, lean=cycle(24, 8, [8, -8], end=22), squash=cycle(24, 8, [0.5, 0], end=22),
     **arms(r={"arm": [(0, 0), (4, 40), (20, 40), (24, 0)], "elbow": [(0, 0), (4, 60), (20, 60), (24, 0)]},
            l={"arm": [(0, 0), (4, -40), (20, -40), (24, 0)], "elbow": [(0, 0), (4, -60), (20, -60), (24, 0)]}))
move("hop_beat", 16, hop=[(0, 0), (2, 0), (6, 6), (10, 0), (16, 0)], legs=[(0, 0), (2, 0.75), (4, -1), (9, -1), (10, 0.6), (16, 0)],
     squash=[(0, 0), (2, 0.75), (5, -0.75), (10, 0.6), (16, 0)], jaw=[(0, 0), (6, 12), (12, 0), (16, 0)])
move("strut", 20, **walk_keys(20, 2, 0.5))

# --- hyped: the guitar god ---------------------------------------------------------
move("headbang", 12, twos=True, pitch=[(0, 0), (4, 32), (8, -12), (12, 0)], lean=[(0, 0), (4, 12), (12, 0)],
     jaw=[(0, 0), (4, 30), (12, 0)], squash=[(0, 0), (4, 1), (12, 0)])
move("windmill", 24, twos=True, lean=[(0, 0), (6, -10), (12, 12), (24, 0)], jaw=[(0, 0), (12, 34), (24, 0)],
     legs=[(0, 0), (6, 0.5), (12, 1), (24, 0)], pitch=[(0, 0), (6, -16), (12, 20), (24, 0)],
     **arms(r={"arm": [(0, 0), (4, 70), (20, 70), (24, 0)], "elbow": [(0, 0), (4, 40), (20, 40), (24, 0)],
               "hand": [(0, 0), (4, 1), (20, 1), (24, 0)]},
            l={"arm": [(0, 0), (6, -170), (10, -60), (12, 40), (18, 30), (24, 0)], "elbow": [(0, 0), (6, -10), (12, 20), (24, 0)],
               "hand": [(0, 0), (4, 1), (20, 1), (24, 0)]}))
move("cheer_jump", 28, twos=True, **hop_keys(28, 4, 18, 18), jaw=[(0, 0), (6, 36), (18, 30), (26, 0), (28, 0)],
     eyes=[(0, 0), (6, -1), (18, -1), (24, 0), (28, 0)],
     **arms(r={"arm": [(0, 0), (4, 20), (8, 155), (18, 150), (26, 0), (28, 0)], "hand": [(0, 0), (8, 1), (18, 1), (26, 0), (28, 0)]},
            l={"arm": [(0, 0), (4, -20), (8, -155), (18, -150), (26, 0), (28, 0)], "hand": [(0, 0), (8, 1), (18, 1), (26, 0), (28, 0)]}))
move("pogo", 36, twos=True, hop=[(0, 0), (2, 0), (6, 13), (10, 0), (12, 0), (16, 15), (20, 0), (22, 0), (26, 13), (30, 0), (36, 0)],
     legs=[(0, 0), (2, 1), (4, -1), (9, -1), (10, 1), (12, 1), (14, -1), (19, -1), (20, 1), (22, 1), (24, -1),
           (29, -1), (30, 1), (33, 0.6), (36, 0)],
     squash=[(0, 0), (2, 1), (5, -1), (10, 1), (12, 1), (15, -1), (20, 1), (22, 1), (25, -1), (30, 1), (33, 0.6), (36, 0)],
     pitch=[(0, 0), (6, -20), (10, 12), (16, -20), (20, 12), (26, -20), (30, 12), (36, 0)], jaw=[(0, 0), (6, 30), (30, 30), (36, 0)],
     **arms(r={"arm": [(0, 0), (6, 160), (10, 100), (16, 160), (20, 100), (26, 160), (30, 100), (36, 0)],
               "hand": [(0, 0), (4, 1), (32, 1), (36, 0)]}))
move("shred", 32, twos=True, pitch=cycle(32, 8, [24, -6], end=30), jaw=[(0, 0), (4, 26), (28, 26), (32, 0)],
     legs=[(0, 0), (4, 1), (28, 1), (32, 0)], lean=[(0, 0), (4, 10), (28, 10), (32, 0)],
     **arms(r={"arm": [(0, 0), (4, 80), (28, 80), (32, 0)], "elbow": [(0, 0), (4, 30), (28, 30), (32, 0)],
               "hand": [(0, 0), (4, 1), (28, 1), (32, 0)]},
            l={"arm": cycle(32, 4, [40, 15], end=30), "elbow": cycle(32, 4, [100, 70], end=30),
               "hand": [(0, 0), (4, 1), (28, 1), (32, 0)]}))
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
     **arms(r={"arm": [(0, 0), (10, 150), (26, 150), (38, 0), (40, 0)]}, l={"arm": [(0, 0), (10, -150), (26, -150), (38, 0), (40, 0)]}))

STANCES = {
    "Asleep":  {"legs": 1, "lean": 14, "pitch": 30, "eyes": 2, "jaw": 6, "armR": 12, "armL": -6, "elbowR": 30, "elbowL": -20},
    "Curious": {"armR": 6, "armL": -6, "elbowR": 10, "elbowL": -10},
    "IntoIt":  {"lean": 4, "legs": 0.25, "armR": 14, "armL": -10, "elbowR": 30, "elbowL": -20, "handR": 1, "handL": 1},
    "Hyped":   {"lean": 6, "legs": 0.5, "jaw": 12, "armR": 24, "armL": -20, "elbowR": 50, "elbowL": -40, "handR": 1, "handL": 1},
}

VOCAB = {
    "Asleep":  [("breathe", 6, "idle"), ("twitch", 1, "idle")],
    "Curious": [("look_l", 3, "idle"), ("look_r", 3, "idle"), ("tilt", 2, "idle"), ("blink", 4, "idle"),
                ("double_blink", 1, "idle"), ("chatter", 2, "idle"), ("scratch", 2, "idle"), ("tap_foot", 2, "idle"),
                ("knuckles", 1, "idle"), ("stretch", 1, "idle"), ("hop_small", 1, "idle"), ("walk", 4, "idle"),
                ("walk_long", 2, "idle"), ("turn_round", 3, "idle"), ("inspect", 2, "idle"), ("shrug", 1, "idle")],
    "IntoIt":  [("nod", 4, "beat"), ("bob", 3, "beat"), ("side_nod", 2, "beat"), ("snap", 3, "beat"), ("strum", 4, "beat"),
                ("fist_pump", 2, "beat"), ("shimmy", 2, "beat"), ("hop_beat", 1, "beat"), ("strut", 2, "beat"),
                ("blink", 3, "idle"), ("chatter", 1, "idle"), ("turn_round", 1, "idle")],
    "Hyped":   [("shred", 5, "beat"), ("windmill", 4, "beat"), ("headbang", 3, "beat"), ("cheer_jump", 3, "beat"),
                ("pogo", 2, "beat"), ("fist_pump", 2, "beat"), ("hop_travel", 1, "beat"), ("turn_hop", 1, "beat"),
                ("blink", 1, "idle")],
}
IDLE_GAPS = {"Asleep": (1800, 4500), "Curious": (500, 1600), "IntoIt": (1200, 3000), "Hyped": (1200, 3000)}
BEAT_MS = {"Asleep": 0, "Curious": 0, "IntoIt": 560, "Hyped": 480}

INTENTS = {
    "Watch":       {"vocab": [("shade_eyes", 3), ("blink", 2), ("tilt", 1)], "gap": (700, 1600)},
    "Bored":       {"vocab": [("tap_foot", 4), ("chatter", 2), ("knuckles", 2), ("scratch", 2), ("inspect", 2),
                              ("shrug", 1), ("stretch", 1), ("walk", 2), ("yawn", 1)], "gap": (900, 2200)},
    "WantsYou":    {"vocab": [("wave", 4), ("beckon", 3), ("shrug", 2), ("hop_small", 1)], "gap": (600, 1400)},
    "Investigate": {"vocab": [("walk", 4), ("inspect", 3), ("hop_small", 1)], "gap": (300, 800)},
}
TURN_MOVE = "turn_round"
ROLES = {"head": "skull", "gust": "armL"}

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
    "breathe": ("zzz", 10), "flutter": ("sweat", 4), "launch": ("bang", 26),
}
