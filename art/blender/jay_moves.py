"""The jay's movement vocabulary for the paper-doll choreographer.

Pure Python (no Blender): tools/build_moves.py turns this into
src/gen/chars/jay/doll_moves.h. Channels and units (see jay_doll.py):
  hop px · legs -1 tuck (airborne)/0 stand/1 crouch/2 low · stride -1..1 (+ near leg forward) · lean° (+forward)
  squash -1 stretch/0/1/2 big/3 fluff · pitch° (+down) · look° · eyes -1 wide/0/1 half/2 closed
  jaw° (+open) · crest° (+flat back, - raised) · tail° (+up) · flapL/flapR° (0 folded .. 165 high V)

A move is keyed per channel as [(frame, value), ...] relative to the stance;
frames between keys follow a smooth spline. Moves should start and end at 0
so they blend in and out of anything. Frames are 30 ms.
"""

MOVES = {}


def move(name, frames, loop=None, loop_until=None, loop_max=0, freeze_ms=0, flip_at=None, twos=False, **channels):
    """x keys are travel forward (toward the beak) and may end away from 0;
    flip_at turns the pet round after that frame (hide it at a hop's apex);
    twos holds each pose two frames (fast moves: the TN panel needs ~60 ms
    to settle, so poses changing every frame smear into each other)."""
    MOVES[name] = {"frames": frames, "loop": loop, "loop_until": loop_until, "loop_max": loop_max,
                   "freeze_ms": freeze_ms, "flip_at": flip_at, "twos": twos, "channels": channels}


def both(keys):
    """Same keys for both wings."""
    return {"flapL": keys, "flapR": keys}


# --- idle: little things a bird does while listening ---------------------------
move("look_l", 44, look=[(0, 0), (7, -30), (36, -28), (44, 0)], pitch=[(0, 0), (7, 4), (36, 4), (44, 0)])
move("look_r", 44, look=[(0, 0), (7, 30), (36, 28), (44, 0)], pitch=[(0, 0), (7, -4), (36, -4), (44, 0)])
move("tilt", 40, look=[(0, 0), (6, 15), (32, 15), (40, 0)], pitch=[(0, 0), (6, -10), (32, -8), (40, 0)],
     crest=[(0, 0), (6, -12), (32, -10), (40, 0)])
move("blink", 5, eyes=[(0, 0), (1, 2), (3, 2), (4, 0), (5, 0)])
move("double_blink", 11, eyes=[(0, 0), (1, 2), (2, 2), (3, 0), (6, 0), (7, 2), (8, 2), (9, 0), (11, 0)])
move("crest_flick", 16, crest=[(0, 0), (4, -30), (9, -24), (16, 0)])
move("preen", 40, pitch=[(0, 0), (8, 30), (30, 28), (40, 0)], look=[(0, 0), (8, 24), (30, 20), (40, 0)],
     eyes=[(0, 0), (8, 1), (30, 1), (40, 0)], flapL=[(0, 0), (8, 18), (30, 18), (40, 0)])
move("tail_flick", 12, tail=[(0, 0), (3, 18), (12, 0)])
move("hop_small", 22, hop=[(0, 0), (4, 0), (9, 7), (14, 0), (22, 0)],
     legs=[(0, 0), (3, 1), (7, -1), (11, -1), (14, 0.8), (17, 0.8), (22, 0)],
     squash=[(0, 0), (3, 1), (8, -1), (14, 0.8), (17, 0.6), (22, 0)], flapL=[(0, 0), (8, 40), (15, 0)],
     flapR=[(0, 0), (8, 40), (15, 0)])

# Getting about the stage (x = travel toward the beak, in pixels; it stays put)
move("hop_fwd", 20, hop=[(0, 0), (4, 0), (9, 6), (14, 0), (20, 0)],
     legs=[(0, 0), (3, 0.75), (7, -1), (11, -1), (14, 0.6), (20, 0)],
     squash=[(0, 0), (3, 0.75), (8, -0.75), (14, 0.6), (20, 0)], x=[(0, 0), (4, 0), (14, 8), (20, 8)],
     **both([(0, 0), (8, 30), (14, 0)]), tail=[(0, 0), (9, 10), (16, 0)])
move("hop_fwd2", 36, hop=[(0, 0), (4, 0), (9, 6), (14, 0), (17, 0), (22, 6), (27, 0), (36, 0)],
     legs=[(0, 0), (3, 0.75), (7, -1), (11, -1), (14, 0.5), (16, 0.5), (20, -1), (24, -1), (27, 0.6), (36, 0)],
     squash=[(0, 0), (3, 0.75), (8, -0.75), (14, 0.5), (16, 0.5), (21, -0.75), (27, 0.6), (36, 0)],
     x=[(0, 0), (4, 0), (14, 8), (17, 8), (27, 16), (36, 16)], **both([(0, 0), (8, 30), (14, 0), (21, 30), (27, 0)]))
# Walking: a step every 10 frames; the hip dips as the legs spread (in the
# art), the head nods a little on each step and the tail sways.
def walk_keys(frames, steps, distance):
    step = frames / steps
    stride = [(0, 0)] + [(round(step * (i + 0.5)), 1 if i % 2 == 0 else -1) for i in range(steps)] + [(frames, 0)]
    nod = [(0, 0)]
    for i in range(steps):
        nod += [(round(step * (i + 0.5)), 3), (round(step * (i + 1)), 0)]
    sway = [(0, 0)] + [(round(step * (i + 1)), 5 if i % 2 == 0 else -4) for i in range(steps - 1)] + [(frames, 0)]
    return {"stride": stride, "x": [(0, 0), (frames, distance)], "pitch": nod, "tail": sway}


move("walk", 40, **walk_keys(40, 4, 18))
move("walk_long", 60, **walk_keys(60, 6, 28), look=[(0, 0), (20, 0), (30, 15), (44, 15), (56, 0), (60, 0)])
# Strut: two swaggering steps per beat, chest out, nodding on the beat.
move("strut", 16, stride=[(0, 0), (4, 1), (12, -1), (16, 0)], x=[(0, 0), (16, 8)],
     pitch=[(0, 0), (4, 12), (8, 0), (12, 12), (16, 0)], lean=[(0, 0), (4, -6), (12, -6), (16, 0)],
     squash=[(0, 0), (4, 0.5), (8, 0), (12, 0.5), (16, 0)], look=[(0, 0), (6, 10), (12, 10), (16, 0)])

# Hop on the beat: a little bounce in place with a wing flick.
move("hop_beat", 16, hop=[(0, 0), (2, 0), (6, 6), (10, 0), (16, 0)],
     legs=[(0, 0), (2, 0.75), (4, -1), (9, -1), (10, 0.6), (16, 0)],
     squash=[(0, 0), (2, 0.75), (5, -0.75), (10, 0.6), (16, 0)], **both([(0, 0), (5, 50), (11, 0)]),
     pitch=[(0, 0), (6, -6), (11, 8), (16, 0)], tail=[(0, 0), (6, 10), (16, 0)])

move("turn_round", 20, flip_at=8, hop=[(0, 0), (3, 0), (8, 6), (13, 0), (20, 0)],
     legs=[(0, 0), (2, 0.75), (6, -1), (10, -1), (13, 0.6), (20, 0)],
     squash=[(0, 0), (2, 0.75), (8, -0.5), (13, 0.6), (20, 0)], **both([(0, 0), (7, 40), (13, 0)]))
move("shuffle", 14, x=[(0, 0), (3, 0), (9, 4), (14, 4)], legs=[(0, 0), (4, 0.5), (8, 0), (11, 0.5), (14, 0)],
     squash=[(0, 0), (4, 0.5), (8, 0), (11, 0.5), (14, 0)], tail=[(0, 0), (5, 8), (14, 0)])

# New behaviours
move("peck", 32, lean=[(0, 0), (8, 18), (24, 18), (32, 0)],
     pitch=[(0, 0), (8, 36), (11, 46), (14, 36), (17, 46), (20, 36), (24, 30), (32, 0)],
     tail=[(0, 0), (8, 14), (24, 14), (32, 0)], squash=[(0, 0), (8, 0.5), (24, 0.5), (32, 0)])
move("look_you", 52, look=[(0, 0), (8, 45), (42, 45), (52, 0)], crest=[(0, 0), (8, -14), (42, -12), (52, 0)],
     eyes=[(0, 0), (24, 0), (25, 2), (27, 2), (28, 0), (52, 0)])
move("shake", 26, look=[(0, 0), (4, 18), (8, -18), (12, 18), (16, -12), (22, 0), (26, 0)],
     squash=[(0, 0), (4, 0.75), (8, -0.5), (12, 0.75), (16, -0.25), (22, 0), (26, 0)],
     crest=[(0, 0), (4, -20), (12, -24), (22, 0), (26, 0)], **both([(0, 0), (6, 30), (12, 10), (18, 25), (26, 0)]),
     tail=[(0, 0), (5, 12), (10, -8), (16, 6), (26, 0)])

# Asleep
# Sleeping breath: a slow swell (the body's shape steps in quarters, so it's
# smooth). No head tilt: a pitch step swaps the whole head's image, which jerks.
move("breathe", 60, squash=[(0, 0), (30, 0.5), (60, 0)])
move("twitch", 14, crest=[(0, 0), (3, -14), (14, 0)])

# --- groove: beat moves --------------------------------------------------------
move("nod", 14, pitch=[(0, 0), (4, 16), (9, -4), (14, 0)], lean=[(0, 0), (4, 5), (14, 0)],
     squash=[(0, 0), (4, 1), (9, 0), (14, 0)], tail=[(0, 0), (5, -10), (14, 0)])
move("bob", 14, pitch=[(0, 0), (4, 8), (14, 0)], lean=[(0, 0), (4, 10), (9, -3), (14, 0)],
     tail=[(0, 0), (5, -12), (14, 0)])
move("side_nod", 14, pitch=[(0, 0), (4, 12), (14, 0)], look=[(0, 0), (4, 14), (14, 0)],
     crest=[(0, 0), (5, -8), (14, 0)])
move("tail_pump", 12, tail=[(0, 0), (3, -18), (8, 6), (12, 0)], squash=[(0, 0), (3, 1), (12, 0)],
     pitch=[(0, 0), (3, 6), (12, 0)])
move("wing_flick", 12, **both([(0, 0), (4, 45), (12, 0)]), pitch=[(0, 0), (4, 8), (12, 0)])

# --- the groove: a bar of two beats, looped in time (see skeleton_moves.py) -------------
def bounce(depth, at=3, back=11, frames=32, beats=2):
    per = frames // beats
    keys = [(0, 0)]
    for b in range(beats):
        keys += [(b * per + at, depth), (b * per + back, depth * 0.08), ((b + 1) * per, 0)]
    return keys


move("groove", 32, legs=bounce(0.5), squash=bounce(0.6), pitch=bounce(12, 5, 13), tail=bounce(-12, 4, 12),
     crest=bounce(-10, 5, 13), look=[(0, 0), (8, 10), (16, 0), (24, -10), (32, 0)])
move("groove_hyped", 32, legs=bounce(0.9), squash=bounce(1.0), pitch=bounce(20, 4, 12), lean=bounce(6, 4, 12),
     tail=bounce(-18, 4, 12), crest=bounce(-24, 4, 12), jaw=bounce(16, 4, 11), **both(bounce(40, 4, 12)))

# --- hyped: beat moves (wing beats every 8 frames; faster blurs on the LCD) -----
# Landings hold the squash a few frames and ease out; an instant rebound reads as a jolt.
move("hop_flap", 28, twos=True, hop=[(0, 0), (2, 0), (8, 18), (12, 21), (16, 18), (22, 0), (28, 0)],
     legs=[(0, 0), (2, 1.25), (5, -1), (19, -1), (22, 1), (25, 0.8), (28, 0)],
     squash=[(0, 0), (2, 1.25), (7, -1), (22, 1), (25, 0.8), (28, 0)],
     **both([(0, 0), (4, 155), (8, 25), (12, 158), (16, 25), (20, 150), (26, 0)]),
     jaw=[(0, 0), (6, 26), (22, 0)], pitch=[(0, 0), (8, -18), (16, -10), (22, 8), (28, 0)],
     crest=[(0, 0), (6, -34), (22, 0)])
move("headbang", 12, pitch=[(0, 0), (4, 30), (8, -12), (12, 0)], lean=[(0, 0), (4, 10), (12, 0)],
     jaw=[(0, 0), (4, 20), (12, 0)], squash=[(0, 0), (4, 1), (12, 0)], tail=[(0, 0), (5, -14), (12, 0)])
move("flap_burst", 16, twos=True, **both([(0, 0), (4, 155), (8, 25), (12, 155), (16, 0)]),
     legs=[(0, 0), (4, 0.5), (12, 0.5), (16, 0)], crest=[(0, 0), (4, -10), (16, 0)])
move("hop_travel", 22, twos=True, hop=[(0, 0), (2, 0), (8, 12), (14, 0), (22, 0)],
     legs=[(0, 0), (2, 1), (5, -1), (11, -1), (14, 0.9), (17, 0.8), (22, 0)],
     squash=[(0, 0), (2, 1), (8, -1), (14, 1), (17, 0.8), (22, 0)], x=[(0, 0), (2, 0), (14, 12), (22, 12)],
     **both([(0, 0), (4, 150), (8, 30), (12, 150), (18, 0)]), jaw=[(0, 0), (8, 20), (18, 0)])
move("turn_hop", 22, twos=True, flip_at=8, hop=[(0, 0), (2, 0), (8, 12), (14, 0), (22, 0)],
     legs=[(0, 0), (2, 1), (5, -1), (11, -1), (14, 0.9), (17, 0.8), (22, 0)],
     squash=[(0, 0), (2, 1), (8, -1), (14, 1), (17, 0.8), (22, 0)],
     **both([(0, 0), (4, 150), (8, 30), (12, 150), (18, 0)]))
# The peak: crouch, burst up, hover flapping like mad (each downstroke lifts
# him, he sags between), wobbling about, then drop and land.
def flight(frames, takeoff, land, base, strokes_every=8):
    wings, hop, lean = [(0, 0), (takeoff - 2, 20)], [(0, 0), (takeoff, 0)], [(0, 0), (takeoff, 8)]
    f, up, i = takeoff + 4, True, 0          # the climb from the ground takes four frames
    while f < land - 10:
        wings.append((f, 160 if up else 20))
        hop.append((f, base + (6 if not up else 0) + (3 if i % 4 == 1 else 0)))
        lean.append((f, (-10, 6, -4, 10)[i % 4]))
        f += strokes_every // 2; up = not up; i += 1
    # glide down: wings out, sinking over ~10 frames
    wings += [(land - 6, 90), (land, 120), (frames, 0)]
    hop += [(land - 5, base * 0.5), (land, 0), (frames, 0)]
    lean += [(land, 0), (frames, 0)]
    return wings, hop, lean


_w, _h, _l = flight(72, 6, 62, 18)
move("frenzy_flight", 72, twos=True, **both(_w), hop=_h, lean=_l,
     legs=[(0, 0), (4, 1.5), (6, 1.5), (9, -1), (56, -1), (60, 0), (63, 1), (67, 0.8), (72, 0)],
     squash=[(0, 0), (4, 1.5), (7, -1), (12, -0.5), (58, -0.5), (63, 1.5), (67, 0.8), (72, 0)],
     pitch=[(0, 0), (6, -20), (20, -28), (32, 10), (44, -28), (58, -10), (72, 0)],
     crest=[(0, 0), (6, -40), (62, -40), (72, 0)], jaw=[(0, 0), (6, 30), (62, 30), (72, 0)],
     eyes=[(0, 0), (6, -1), (58, -1), (64, 0)],
     tail=[(0, 0), (10, -14), (18, 10), (26, -14), (34, 10), (42, -14), (50, 10), (72, 0)])
# Pogo: three quick flapping jumps in a row, head thrown back.
move("pogo", 36, twos=True, hop=[(0, 0), (2, 0), (6, 13), (10, 0), (12, 0), (16, 15), (20, 0), (22, 0), (26, 13), (30, 0), (36, 0)],
     legs=[(0, 0), (2, 1), (4, -1), (9, -1), (10, 1), (12, 1), (14, -1), (19, -1), (20, 1), (22, 1), (24, -1),
           (29, -1), (30, 1), (33, 0.6), (36, 0)],
     squash=[(0, 0), (2, 1), (5, -1), (10, 1), (12, 1), (15, -1), (20, 1), (22, 1), (25, -1), (30, 1), (33, 0.6), (36, 0)],
     **both([(0, 0), (3, 20), (6, 160), (10, 30), (13, 20), (16, 160), (20, 30), (23, 20), (26, 160), (30, 30), (36, 0)]),
     pitch=[(0, 0), (6, -24), (10, 10), (16, -24), (20, 10), (26, -24), (30, 10), (36, 0)],
     jaw=[(0, 0), (6, 28), (30, 28), (36, 0)], crest=[(0, 0), (6, -36), (30, -36), (36, 0)])
move("rock", 24, lean=[(0, 0), (6, 14), (18, -12), (24, 0)], tail=[(0, 0), (6, -12), (18, 10), (24, 0)],
     pitch=[(0, 0), (6, -8), (18, 8), (24, 0)], **both([(0, 0), (6, 30), (12, 0), (18, 30), (24, 0)]))

# --- reactions -----------------------------------------------------------------
move("startle", 30, twos=True, x=[(0, 0), (2, 0), (8, -6), (14, -8), (30, -8)],
     lean=[(0, 0), (6, -14), (16, -10), (24, 4), (30, 0)],
     hop=[(0, 0), (2, 0), (6, 9), (13, 0), (30, 0)],
     legs=[(0, 0), (2, 1), (5, -1), (11, -1), (14, 0.9), (18, 0.7), (24, 0)],
     squash=[(0, 0), (2, 1), (6, -1), (14, 1), (18, 0.7), (24, 0)], eyes=[(0, 0), (3, -1), (20, -1), (26, 0)],
     crest=[(0, 0), (5, -40), (20, -34), (30, 0)], jaw=[(0, 0), (5, 28), (18, 20), (28, 0)],
     pitch=[(0, 0), (6, -14), (18, -8), (30, 0)], **both([(0, 0), (6, 150), (16, 125), (28, 0)]))
move("flutter", 28, twos=True, loop=(4, 16), **both([(0, 0), (4, 160), (8, 30), (12, 160), (16, 30), (20, 160), (27, 0)]),
     hop=[(0, 0), (3, 0), (6, 6), (10, 3), (14, 6), (18, 3), (21, 6), (25, 0), (27, 0)],
     legs=[(0, 0), (2, 1), (4, -1), (23, -1), (25, 1), (27, 0)], squash=[(0, 0), (2, 1), (5, -0.5), (23, -0.5), (25, 1), (27, 0)],
     crest=[(0, 0), (4, -30), (20, -30), (27, 0)], jaw=[(0, 0), (4, 16), (20, 16), (27, 0)])
move("sing", 40, loop=(10, 16), loop_until="SustainEnd", loop_max=6000,
     pitch=[(0, 0), (10, -24), (18, -26), (26, -24), (39, 0)], jaw=[(0, 0), (10, 34), (26, 34), (39, 0)],
     crest=[(0, 0), (10, -36), (26, -36), (39, 0)], eyes=[(0, 0), (10, 1), (26, 1), (39, 0)],
     look=[(0, 0), (10, 0), (18, 8), (26, 0), (39, 0)], **both([(0, 0), (10, 28), (18, 34), (26, 28), (39, 0)]))
move("launch", 48, twos=True, loop=(12, 8), loop_until="SwellPeak", loop_max=5000,
     legs=[(0, 0), (12, 2), (20, 2), (23, -1), (34, -1), (37, 1), (48, 0)],
     squash=[(0, 0), (12, 2), (16, 2), (20, 2), (25, -1), (31, 0), (38, 2), (48, 0)],
     lean=[(0, 0), (12, 14), (20, 14), (26, 0), (48, 0)], crest=[(0, 0), (12, 20), (20, 20), (26, -40), (48, 0)],
     eyes=[(0, 0), (12, 1), (20, 1), (25, -1), (40, 0)], jaw=[(0, 0), (20, 0), (26, 22), (40, 0)],
     hop=[(0, 0), (20, 0), (26, 22), (30, 25), (34, 22), (38, 0), (48, 0)],
     **both([(0, 0), (12, 18), (20, 18), (26, 160), (30, 40), (34, 150), (38, 60), (48, 0)]))
move("point", 24, freeze_ms=450, flapL=[(0, 0), (4, 90), (16, 86), (24, 0)],
     look=[(0, 0), (4, -10), (16, -8), (24, 0)], crest=[(0, 0), (4, -30), (16, -26), (24, 0)],
     jaw=[(0, 0), (4, 12), (16, 10), (24, 0)])
move("wake", 30, hop=[(0, 0), (3, 8), (10, 0), (30, 0)], eyes=[(0, 0), (3, -1), (12, -1), (18, 0)],
     crest=[(0, 0), (3, -40), (20, -10), (30, 0)], **both([(0, 0), (3, 60), (12, 0)]),
     look=[(0, 0), (8, 0), (13, 30), (20, -30), (28, 0), (30, 0)], jaw=[(0, 0), (3, 14), (10, 0)])
move("yawn", 34, jaw=[(0, 0), (10, 36), (18, 0)], **both([(0, 0), (10, 100), (18, 0)]),
     eyes=[(0, 0), (10, 2), (18, 1), (34, 0)], pitch=[(0, 0), (10, -16), (18, 6), (34, 0)])


# --- moods ---------------------------------------------------------------------
STANCES = {
    "Asleep":  {"legs": 2, "squash": 3, "pitch": 24, "eyes": 2, "crest": 45, "tail": 12, "flapL": 1, "flapR": 1},
    "Curious": {"crest": -6, "flapL": 3, "flapR": 3},
    "IntoIt":  {"lean": 4, "crest": -14, "flapL": 6, "flapR": 6},
    "Hyped":   {"lean": 6, "crest": -34, "jaw": 10, "flapL": 10, "flapR": 10},
}

# (move, weight, kind) — kind "idle" plays on a random gap, "beat" on picks
# (or the mood's tempo when nothing is being played).
VOCAB = {
    "Asleep":  [("breathe", 6, "idle"), ("twitch", 1, "idle")],
    "Curious": [("look_l", 3, "idle"), ("look_r", 3, "idle"), ("tilt", 2, "idle"), ("blink", 4, "idle"),
                ("double_blink", 1, "idle"), ("crest_flick", 2, "idle"), ("preen", 1, "idle"),
                ("tail_flick", 2, "idle"), ("hop_small", 3, "idle"), ("hop_fwd", 4, "idle"), ("hop_fwd2", 3, "idle"),
                ("turn_round", 3, "idle"), ("peck", 2, "idle"), ("look_you", 2, "idle"), ("shake", 1, "idle")],
    "IntoIt":  [("wing_flick", 2, "beat"), ("hop_beat", 3, "beat"), ("hop_fwd", 2, "beat"), ("tail_pump", 2, "beat"),
                ("side_nod", 1, "beat"), ("blink", 3, "idle"), ("crest_flick", 1, "idle"),
                ("look_you", 1, "idle"), ("shake", 1, "idle"), ("turn_round", 1, "idle")],
    "Hyped":   [("frenzy_flight", 6, "beat"), ("pogo", 4, "beat"), ("hop_flap", 4, "beat"), ("flap_burst", 1, "beat"),
                ("headbang", 1, "beat"), ("hop_travel", 1, "beat"), ("turn_hop", 1, "beat"), ("blink", 1, "idle")],
}
IDLE_GAPS = {"Asleep": (1800, 4500), "Curious": (500, 1600), "IntoIt": (1200, 3000), "Hyped": (1200, 3000)}
BEAT_MS = {"Asleep": 0, "Curious": 0, "IntoIt": 560, "Hyped": 500}
GROOVES = {"IntoIt": ("groove", 2), "Hyped": ("groove_hyped", 2)}   # (move, beats it spans)

# What he does when the Mind wants something (idle vocabularies; see
# docs/superpowers/specs/2026-10-30-inner-life-design.md). Gaze is the Mind's:
# these are what the body does meanwhile.
INTENTS = {
    "Watch":       {"vocab": [("blink", 3), ("tail_flick", 2), ("crest_flick", 1)], "gap": (900, 2000)},
    "Bored":       {"vocab": [("preen", 3), ("yawn", 2), ("shake", 1), ("double_blink", 2), ("tail_flick", 1),
                              ("peck", 1)], "gap": (1800, 4000),
                    "stance": {"eyes": 1, "pitch": 12, "crest": 40, "tail": -10, "squash": 1, "flapL": -2, "flapR": -2}},
    "WantsYou":    {"vocab": [("hop_small", 3), ("crest_flick", 3), ("tail_flick", 2), ("wing_flick", 2),
                              ("hop_fwd", 1)], "gap": (600, 1400), "stance": {"crest": -20, "squash": -0.5}},
    "Investigate": {"vocab": [("hop_fwd", 4), ("peck", 3), ("hop_small", 1)], "gap": (300, 800)},
}
TURN_MOVE = "turn_round"
# Roles the engine needs: the head (gaze, marks), the channel that gusts leaves,
# and the moves the Mind uses to go up to a leaf and have a go at it.
ROLES = {"head": "head", "gust": "flapL", "approach": "hop_fwd", "reach": "peck", "reach_px": 6}

REACTIONS = {
    "BigHit": ["startle"], "Flurry": ["flutter"], "Sustain": ["sing"], "Swell": ["launch"], "Cut": ["point"],
    "Wake": ["wake"], "DriftOff": ["yawn"],
}


# --- expression marks ------------------------------------------------------------
# Pixel drawings: '.' clear, '#' ink, 'n' navy, 's' sky, 'w' white, 'b' blue.
MARK_COLOURS = {"#": "ink", "n": "navy", "s": "sky", "w": "white", "b": "blue", "g": "grey"}
MARK_IMAGES = {
    "bang": [".##.", "####", "####", ".##.", ".##.", ".##.", "....", ".##.", ".##."],
    "bang_s": [".#.", "###", ".#.", ".#.", "...", ".#."],
    "question": [".###.", "##.##", "...##", "..##.", ".##..", ".##..", ".....", ".##..", ".##.."],
    "note": ["..##.", "..#.#", "..#..", ".##..", "###..", ".#..."],
    "z_small": ["nnnn", "..n.", ".n..", "nnnn"],
    "z_big": ["nnnnn", "...n.", "..n..", ".n...", "nnnnn"],
    "drop": [".#.", "#s#", "#s#", ".#."],
}


def path(img, frames, start, end, sway=0, sway_period=12):
    """Frames moving `img` from start to end (dx, dy offsets from the head pivot)."""
    import math
    out = []
    for f in range(frames):
        u = f / max(1, frames - 1)
        dx = start[0] + (end[0] - start[0]) * u + sway * math.sin(2 * math.pi * f / sway_period)
        dy = start[1] + (end[1] - start[1]) * u
        out.append((img, round(dx), round(dy)))
    return out


# Offsets: head pivot -> mark's top-left, with the beak facing screen-left
# (so + dx is behind the head). Mirrored automatically when the jay turns.
MARKS = {
    "bang": [("bang_s", 4, -40)] * 2 + path("bang", 16, (4, -44), (4, -46)) + [("bang_s", 4, -42)] * 2,
    "question": path("question", 24, (6, -44), (6, -46)),
    "notes": path("note", 30, (-14, -26), (-24, -50), sway=2),
    "zzz": path("z_small", 22, (8, -22), (14, -34)) + path("z_big", 26, (14, -38), (22, -52), sway=1, sway_period=26),
    "sweat": path("drop", 14, (10, -16), (22, -4)),
}
# move -> (mark, frame it pops at; the move must be at full strength by then)
MOVE_MARKS = {
    "startle": ("bang", 2), "tilt": ("question", 8), "sing": ("notes", 10),
    "breathe": ("zzz", 10), "flutter": ("sweat", 4), "launch": ("bang", 26),
}
