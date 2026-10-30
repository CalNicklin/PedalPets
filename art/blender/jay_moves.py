"""The jay's movement vocabulary for the paper-doll choreographer.

Pure Python (no Blender): tools/build_moves.py turns this into
src/gen/doll_moves.h. Channels and units (see jay_doll.py):
  hop px · legs -1 tuck (airborne)/0 stand/1 crouch/2 low · lean° (+forward)
  squash -1 stretch/0/1/2 big/3 fluff · pitch° (+down) · look° · eyes -1 wide/0/1 half/2 closed
  jaw° (+open) · crest° (+flat back, - raised) · tail° (+up) · flapL/flapR° (0 folded .. 165 high V)

A move is keyed per channel as [(frame, value), ...] relative to the stance;
frames between keys follow a smooth spline. Moves should start and end at 0
so they blend in and out of anything. Frames are 30 ms.
"""

MOVES = {}


def move(name, frames, loop=None, loop_until=None, loop_max=0, freeze_ms=0, **channels):
    MOVES[name] = {"frames": frames, "loop": loop, "loop_until": loop_until, "loop_max": loop_max,
                   "freeze_ms": freeze_ms, "channels": channels}


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

# Asleep
move("breathe", 60, pitch=[(0, 0), (30, 5), (60, 0)], tail=[(0, 0), (30, -4), (60, 0)])
move("twitch", 14, crest=[(0, 0), (3, -14), (14, 0)], tail=[(0, 0), (4, 10), (14, 0)])

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

# --- hyped: beat moves (wing beats every 8 frames; faster blurs on the LCD) -----
# Landings hold the squash a few frames and ease out; an instant rebound reads as a jolt.
move("hop_flap", 22, hop=[(0, 0), (2, 0), (8, 14), (14, 0), (22, 0)],
     legs=[(0, 0), (2, 1), (5, -1), (11, -1), (14, 0.9), (17, 0.8), (22, 0)],
     squash=[(0, 0), (2, 1), (8, -1), (14, 1), (17, 0.8), (22, 0)],
     **both([(0, 0), (4, 150), (8, 30), (12, 150), (18, 0)]),
     jaw=[(0, 0), (8, 24), (18, 0)], pitch=[(0, 0), (8, -10), (14, 8), (22, 0)])
move("headbang", 12, pitch=[(0, 0), (4, 30), (8, -12), (12, 0)], lean=[(0, 0), (4, 10), (12, 0)],
     jaw=[(0, 0), (4, 20), (12, 0)], squash=[(0, 0), (4, 1), (12, 0)], tail=[(0, 0), (5, -14), (12, 0)])
move("flap_burst", 16, **both([(0, 0), (4, 155), (8, 25), (12, 155), (16, 0)]),
     hop=[(0, 0), (4, 4), (8, 1), (12, 4), (16, 0)], crest=[(0, 0), (4, -10), (16, 0)])
move("rock", 24, lean=[(0, 0), (6, 14), (18, -12), (24, 0)], tail=[(0, 0), (6, -12), (18, 10), (24, 0)],
     pitch=[(0, 0), (6, -8), (18, 8), (24, 0)], **both([(0, 0), (6, 30), (12, 0), (18, 30), (24, 0)]))

# --- reactions -----------------------------------------------------------------
move("startle", 30, lean=[(0, 0), (6, -14), (16, -10), (24, 4), (30, 0)],
     hop=[(0, 0), (2, 0), (6, 9), (13, 0), (30, 0)],
     legs=[(0, 0), (2, 1), (5, -1), (11, -1), (14, 0.9), (18, 0.7), (24, 0)],
     squash=[(0, 0), (2, 1), (6, -1), (14, 1), (18, 0.7), (24, 0)], eyes=[(0, 0), (3, -1), (20, -1), (26, 0)],
     crest=[(0, 0), (5, -40), (20, -34), (30, 0)], jaw=[(0, 0), (5, 28), (18, 20), (28, 0)],
     pitch=[(0, 0), (6, -14), (18, -8), (30, 0)], **both([(0, 0), (6, 150), (16, 125), (28, 0)]))
move("flutter", 28, loop=(4, 16), **both([(0, 0), (4, 160), (8, 30), (12, 160), (16, 30), (20, 160), (27, 0)]),
     hop=[(0, 0), (4, 6), (8, 2), (12, 6), (16, 2), (20, 6), (27, 0)],
     crest=[(0, 0), (4, -30), (20, -30), (27, 0)], jaw=[(0, 0), (4, 16), (20, 16), (27, 0)])
move("sing", 40, loop=(10, 16), loop_until="SustainEnd", loop_max=6000,
     pitch=[(0, 0), (10, -24), (18, -26), (26, -24), (39, 0)], jaw=[(0, 0), (10, 34), (26, 34), (39, 0)],
     crest=[(0, 0), (10, -36), (26, -36), (39, 0)], eyes=[(0, 0), (10, 1), (26, 1), (39, 0)],
     look=[(0, 0), (10, 0), (18, 8), (26, 0), (39, 0)], **both([(0, 0), (10, 28), (18, 34), (26, 28), (39, 0)]))
move("launch", 48, loop=(12, 8), loop_until="SwellPeak", loop_max=5000,
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
                ("tail_flick", 2, "idle"), ("hop_small", 1, "idle")],
    "IntoIt":  [("nod", 4, "beat"), ("bob", 3, "beat"), ("side_nod", 2, "beat"), ("tail_pump", 2, "beat"),
                ("wing_flick", 1, "beat"), ("blink", 3, "idle"), ("crest_flick", 1, "idle")],
    "Hyped":   [("hop_flap", 4, "beat"), ("headbang", 3, "beat"), ("flap_burst", 3, "beat"), ("rock", 2, "beat"),
                ("blink", 2, "idle"), ("crest_flick", 1, "idle")],
}
IDLE_GAPS = {"Asleep": (1800, 4500), "Curious": (500, 1600), "IntoIt": (1200, 3000), "Hyped": (1200, 3000)}
BEAT_MS = {"Asleep": 0, "Curious": 0, "IntoIt": 560, "Hyped": 480}

REACTIONS = {
    "BigHit": ["startle"], "Flurry": ["flutter"], "Sustain": ["sing"], "Swell": ["launch"], "Cut": ["point"],
    "Wake": ["wake"], "DriftOff": ["yawn"],
}
