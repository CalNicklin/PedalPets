"""Shared helpers for character move files (art/blender/<char>_moves.py).

Pure Python: tools/build_moves.py loads a moves file, which builds its moves
with these helpers. A move is keyed per channel as [(frame, value), ...]
relative to the stance; frames are 30 ms.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
from build_moves import spline  # noqa: E402  (the curve the build samples moves with)


def new_registry():
    """A fresh MOVES dict and its move() function."""
    moves = {}

    def move(name, frames, loop=None, loop_until=None, loop_max=0, freeze_ms=0, flip_at=None, twos=False,
             solo=False, **channels):
        """x keys are travel forward and may end away from 0; flip_at turns the
        pet round after that frame (hide it in the air); twos holds each pose
        two frames (fast moves: the TN panel needs ~60 ms to settle); solo is a
        posture (lying back, sitting) no other idle move starts during."""
        moves[name] = {"frames": frames, "loop": loop, "loop_until": loop_until, "loop_max": loop_max,
                       "freeze_ms": freeze_ms, "flip_at": flip_at, "twos": twos, "solo": solo, "channels": channels}
    return moves, move


def cycle(frames, period, values, start=0, end=None, offset=0):
    """Keys that repeat `values` every `period` frames from `start` to `end`, 0 at both ends."""
    end = frames if end is None else end
    keys = [(0, 0)]
    if start > 0:
        keys.append((start, 0))
    step = period / len(values)
    f, i = start + step, 0
    while f < end - 1e-9:
        keys.append((round(f + offset), values[i % len(values)]))
        f += step
        i += 1
    keys.append((end, 0))
    if end < frames:
        keys.append((frames, 0))
    out = []
    for k in keys:                       # drop duplicate frames (keep the last)
        if out and out[-1][0] >= k[0]:
            out[-1] = (out[-1][0], k[1]) if out[-1][0] == k[0] else out[-1]
            continue
        out.append(k)
    return out


def planted_travel(stride_keys, frames, leg_px, stride_deg, step=0.25):
    """x keys (one per frame) that move the body exactly as far as the planted
    foot swings back: sum of |d(leg * sin(stride angle))|, from the stride as
    it will be shown (the build's curve, in the leg images' `step`s), so the
    body moves when and as far as the visible foot plants."""
    x, prev, keys = 0.0, 0.0, [(0, 0)]
    for f in range(1, frames + 1):
        shown = round(spline(stride_keys, f) / step) * step
        s = math.sin(math.radians(stride_deg * shown))
        x += leg_px * abs(s - prev)
        prev = s
        keys.append((f, round(x, 3)))
    return keys


def path(img, frames, start, end, sway=0, sway_period=12):
    """Mark frames moving `img` from start to end (dx, dy offsets from the anchor pivot)."""
    out = []
    for f in range(frames):
        u = f / max(1, frames - 1)
        dx = start[0] + (end[0] - start[0]) * u + sway * math.sin(2 * math.pi * f / sway_period)
        dy = start[1] + (end[1] - start[1]) * u
        out.append((img, round(dx), round(dy)))
    return out


# Pixel drawings for expression marks: '.' clear, '#' ink, 'n' dark, 's' light.
MARK_IMAGES = {
    "bang": [".##.", "####", "####", ".##.", ".##.", ".##.", "....", ".##.", ".##."],
    "bang_s": [".#.", "###", ".#.", ".#.", "...", ".#."],
    "question": [".###.", "##.##", "...##", "..##.", ".##..", ".##..", ".....", ".##..", ".##.."],
    "note": ["..##.", "..#.#", "..#..", ".##..", "###..", ".#..."],
    "z_small": ["nnnn", "..n.", ".n..", "nnnn"],
    "z_big": ["nnnnn", "...n.", "..n..", ".n...", "nnnnn"],
    "drop": [".#.", "#s#", "#s#", ".#."],
}
