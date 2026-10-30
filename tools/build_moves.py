#!/usr/bin/env python3
"""Compile a character's movement vocabulary into firmware tables.

Usage:  python3 tools/build_moves.py <moves.py> <parts.json>

Samples every move channel per frame (smooth spline through the keys, flat at
the ends) and writes src/gen/doll_moves.h with the Choreography for the doll.
Channel order, palette and parts come from parts.json. Expression marks are
also written as PNGs to <parts dir>/marks/ for the timeline tools.
"""

import importlib.util
import json
import struct
import sys
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "src" / "gen"
MOODS = ["Asleep", "Curious", "IntoIt", "Hyped"]
TRIGGERS = ["DriftOff", "Sustain", "Swell", "Flurry", "Cut", "BigHit", "Wake"]
EVENTS = ["Pick", "BigHit", "Flurry", "SustainStart", "SustainEnd", "SwellStart", "SwellPeak", "Cut"]


class MovesError(Exception):
    pass


def spline(keys, f):
    """Cubic Hermite through (frame, value) keys; zero slope at both ends."""
    ts = [k[0] for k in keys]
    vs = [k[1] for k in keys]
    if f <= ts[0]:
        return vs[0]
    if f >= ts[-1]:
        return vs[-1]
    i = max(k for k in range(len(ts) - 1) if ts[k] <= f)
    t0, t1, p0, p1 = ts[i], ts[i + 1], vs[i], vs[i + 1]

    def slope(k):
        if k == 0 or k == len(ts) - 1:
            return 0.0
        return (vs[k + 1] - vs[k - 1]) / (ts[k + 1] - ts[k - 1])

    h = t1 - t0
    m0, m1 = slope(i) * h, slope(i + 1) * h
    u = (f - t0) / h
    return ((2 * u**3 - 3 * u**2 + 1) * p0 + (u**3 - 2 * u**2 + u) * m0
            + (-2 * u**3 + 3 * u**2) * p1 + (u**3 - u**2) * m1)


def load(path):
    spec = importlib.util.spec_from_file_location("moves", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(mod, channels):
    names = list(mod.MOVES)
    moves, tracks, samples = [], [], []
    for name in names:
        m = mod.MOVES[name]
        first_track = len(tracks)
        for ch, keys in m["channels"].items():
            if ch not in channels:
                raise MovesError(f"move {name}: unknown channel {ch!r}")
            # Travel (x) is the one channel allowed to end away from 0: it's where the pet goes.
            if keys[0][1] != 0 or (keys[-1][1] != 0 and ch != "x"):
                raise MovesError(f"move {name}.{ch}: must start and end at 0 to blend")
            tracks.append((channels.index(ch), len(samples)))
            samples += [int(round(spline(keys, f) * 4)) for f in range(m["frames"])]
        loop_from, loop_len = m["loop"] or (0, 0)
        until = m["loop_until"] or "None"
        if until != "None" and until not in EVENTS:
            raise MovesError(f"move {name}: unknown loop_until {until!r}")
        flip = m.get("flip_at")
        if flip is not None and not 0 <= flip < m["frames"]:
            raise MovesError(f"move {name}: flip_at outside its frames")
        mark, mark_at = getattr(mod, "MOVE_MARKS", {}).get(name, (None, 0))
        mark_names = list(getattr(mod, "MARKS", {}))
        if mark is not None and mark not in mark_names:
            raise MovesError(f"move {name}: unknown mark {mark!r}")
        moves.append((name, m["frames"], len(m["channels"]), first_track, loop_from, loop_len,
                      until, m["loop_max"], m["freeze_ms"], 0 if flip is None else flip + 1,
                      0 if mark is None else mark_names.index(mark) + 1, mark_at))

    vocab, styles = [], []
    for mood in MOODS:
        first = len(vocab)
        for mv, weight, kind in mod.VOCAB.get(mood, []):
            if mv not in names:
                raise MovesError(f"vocab {mood}: unknown move {mv!r}")
            vocab.append((names.index(mv), weight, "Beat" if kind == "beat" else "Idle"))
        stance = [0] * len(channels)
        for ch, v in mod.STANCES.get(mood, {}).items():
            stance[channels.index(ch)] = int(round(v * 4))
        gap = mod.IDLE_GAPS.get(mood, (60000, 60000))
        styles.append((stance, first, len(vocab) - first, gap[0], gap[1], mod.BEAT_MS.get(mood, 0)))

    reactions, ids = [], []
    for trig, mvs in mod.REACTIONS.items():
        if trig not in TRIGGERS:
            raise MovesError(f"reaction: unknown trigger {trig!r}")
        reactions.append((trig, len(ids), len(mvs)))
        ids += [names.index(m) for m in mvs]
    return {"moves": moves, "tracks": tracks, "samples": samples, "vocab": vocab, "styles": styles,
            "reactions": reactions, "ids": ids, "channels": channels}


def build_marks(mod, palette_names):
    """Mark images as 4-bit palette rows (index = palette position + 1), plus
    the animation frame table."""
    images = list(getattr(mod, "MARK_IMAGES", {}))
    pix, sizes = [], []
    for name in images:
        rows = mod.MARK_IMAGES[name]
        w = max(len(r) for r in rows)
        data = []
        for r in rows:
            idx = [0 if ch == "." else palette_names.index(mod.MARK_COLOURS[ch]) + 1 for ch in r.ljust(w, ".")]
            idx += [0] * (len(idx) % 2)
            data += [(idx[i] << 4) | idx[i + 1] for i in range(0, len(idx), 2)]
        pix.append(data)
        sizes.append((w, len(rows)))
    anims, frames = [], []
    for name, fr in getattr(mod, "MARKS", {}).items():
        anims.append((name, len(frames), len(fr)))
        frames += [(images.index(img), dx, dy) for img, dx, dy in fr]
    return {"images": images, "pixels": pix, "sizes": sizes, "anims": anims, "frames": frames}


def write_png(path, rows, colours):
    """Tiny RGBA PNG writer (no Pillow needed) for the timeline tools."""
    w, h = max(len(r) for r in rows), len(rows)
    raw = b""
    for r in rows:
        raw += b"\x00" + b"".join(bytes(colours[c]) + b"\xff" if c != "." else b"\x00\x00\x00\x00"
                                  for c in r.ljust(w, "."))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def emit(t, marks, anchor):
    out = ["// Auto-generated by tools/build_moves.py — do not edit.", "#pragma once",
           '#include "../core/choreo.h"', "", "namespace doll_gen {", ""]
    for i, data in enumerate(marks["pixels"]):
        out.append(f"static const uint8_t MARK_PIX_{i}[] = {{" + ", ".join(f"0x{v:02X}" for v in data) + "};")
    out.append("static const uint8_t* const MARK_PIXELS[] = {"
               + ", ".join(f"MARK_PIX_{i}" for i in range(len(marks["pixels"]))) + "};")
    out.append("static const MarkSize MARK_SIZES[] = {" + ", ".join(f"{{{w}, {h}}}" for w, h in marks["sizes"]) + "};")
    out.append("static const MarkFrame MARK_FRAMES[] = {"
               + ", ".join(f"{{{i}, {dx}, {dy}}}" for i, dx, dy in marks["frames"]) + "};")
    out.append("static const MarkAnim MARK_ANIMS[] = {" + ", ".join(f"{{{f}, {n}}}" for _, f, n in marks["anims"]) + "};")
    out.append("")
    out.append("static const int16_t MOVE_SAMPLES[] = {" + ", ".join(map(str, t["samples"])) + "};")
    out.append("static const MoveTrack MOVE_TRACKS[] = {" + ", ".join(f"{{{c}, {f}}}" for c, f in t["tracks"]) + "};")
    out.append("static const Move MOVES[] = {")
    for name, frames, ntr, ft, lf, ll, until, lmax, freeze, flip, mark, mark_at in t["moves"]:
        out.append(f"  {{{frames}, {ntr}, {ft}, {lf}, {ll}, EventType::{until}, {lmax}, {freeze}, {flip}, "
                   f"{mark}, {mark_at}}},  // {name}")
    out.append("};")
    out.append("static const char* const MOVE_NAMES[] = {" + ", ".join(f'"{m[0]}"' for m in t["moves"]) + "};")
    out.append("static const VocabEntry VOCAB[] = {"
               + ", ".join(f"{{{m}, {w}, MoveKind::{k}}}" for m, w, k in t["vocab"]) + "};")
    out.append("static const uint8_t REACTION_MOVE_IDS[] = {" + ", ".join(map(str, t["ids"])) + "};")
    out.append("static const ReactionMoves REACTIONS[] = {"
               + ", ".join(f"{{Trigger::{tr}, {f}, {n}}}" for tr, f, n in t["reactions"]) + "};")
    out += ["", "static const Choreography CHOREO = {",
            f"  MOVES, {len(t['moves'])}, MOVE_TRACKS, MOVE_SAMPLES,", "  {"]
    for stance, first, count, gmin, gmax, beat in t["styles"]:
        out.append(f"    {{{{{', '.join(map(str, stance))}}}, {first}, {count}, {gmin}, {gmax}, {beat}}},")
    ch = t["channels"]
    xi = ch.index("x") if "x" in ch else -1
    fi = ch.index("face") if "face" in ch else -1
    out += ["  },", f"  VOCAB, REACTIONS, {len(t['reactions'])}, REACTION_MOVE_IDS, {len(ch)}, {xi}, {fi},",
            f"  MARK_ANIMS, MARK_FRAMES, {len(marks['anims'])}, MARK_SIZES, {anchor},",
            "};", "", "}  // namespace doll_gen", ""]
    return "\n".join(out)


def main():
    mod = load(sys.argv[1])
    parts_json = Path(sys.argv[2])
    meta = json.loads(parts_json.read_text())
    channels = meta["channels"]
    palette = meta["palette"]
    names = [c["name"] for c in palette]
    part_names = [p["name"] for p in meta["parts"]]
    anchor = part_names.index("head") if "head" in part_names else -1
    try:
        t = build(mod, channels)
        marks = build_marks(mod, names)
    except MovesError as e:
        print(f"build_moves: {e}", file=sys.stderr)
        sys.exit(1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "doll_moves.h").write_text(emit(t, marks, anchor))
    # Marks as PNGs + layout for tools/doll_timeline.py
    mdir = parts_json.parent / "marks"
    mdir.mkdir(exist_ok=True)
    colours = {ch: tuple(int(c["out"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
               for ch, name in getattr(mod, "MARK_COLOURS", {}).items() for c in palette if c["name"] == name}
    for name in marks["images"]:
        write_png(mdir / f"{name}.png", mod.MARK_IMAGES[name], colours)
    (mdir / "marks.json").write_text(json.dumps({"images": marks["images"]}))
    print(f"build_moves: {len(t['moves'])} moves, {len(t['samples'])} samples")


if __name__ == "__main__":
    main()
