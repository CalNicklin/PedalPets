#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Re-render a frame timeline (from the simulator or device telemetry) and
report how smooth it is.

Usage:
  uv run tools/render_timeline.py timeline.csv [--gif out.gif]
         [--strip out.png --from MS --to MS] [--scale N]

Timeline CSV columns: t_ms,pose,eye,mood,energy,reaction,step,frame_us
(frame_us is empty for simulator runs).
"""

import argparse
import csv
import statistics
import sys
import tomllib
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import build_art as ba  # noqa: E402

SCREEN_W, SCREEN_H = 160, 128
CANVAS_X = (SCREEN_W - 96) // 2      # mirrors renderer_tft.cpp
CANVAS_Y = SCREEN_H - 112 - 4
EYES = ["Auto", "Open", "Blink", "LookL", "LookR", "Wide", "HappyClosed"]
MOODS = ["Asleep", "Curious", "IntoIt", "Hyped"]
WHITE = (255, 255, 255)
SNAP_PX = 6          # pose-to-pose anchor shift that reads as a jump
FLASH_MS = 70        # a pose shown for less than this reads as a flicker


def load_poses():
    m = tomllib.loads(ba.MANIFEST.read_text())
    raw = ba.collect_poses(m)
    names = list(raw)
    return names, [ba.process_pose(n, raw[n]) for n in names]


def load_rows(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["t"] = int(r["t_ms"])
        r["pose"] = int(r["pose"])
        r["eye"] = int(r["eye"])
        r["mood"] = int(r["mood"])
        r["frame_us"] = int(r["frame_us"]) if r.get("frame_us") else None
    return rows


def draw_eyes(d, cx, cy, eye):
    """Mirror of RendererTft::drawEyes placeholder primitives."""
    name = EYES[eye]
    dx = -2 if name == "LookL" else 2 if name == "LookR" else 0
    for side in (-1, 1):
        x = cx + side * 4 + dx
        if name == "Blink":
            d.line([(x - 1, cy), (x + 1, cy)], fill=WHITE)
        elif name == "HappyClosed":
            d.line([(x - 1, cy), (x, cy - 1), (x + 1, cy)], fill=WHITE)
        elif name == "Wide":
            d.rectangle([x - 2, cy - 2, x + 1, cy + 1], fill=WHITE)
        else:
            d.rectangle([x - 1, cy - 1, x + 1, cy + 1], fill=WHITE)


def render(row, poses):
    img = Image.new("RGB", (SCREEN_W, SCREEN_H), (0, 0, 0))
    p = poses[row["pose"]]
    img.paste(p["image"], (CANVAS_X + p["x"], CANVAS_Y + p["y"]))
    if p["ex"] != -1:
        draw_eyes(ImageDraw.Draw(img), CANVAS_X + p["ex"], CANVAS_Y + p["ey"], row["eye"])
    return img


def anchor(p):
    """Horizontal centre and bottom of the pose's drawn pixels, in canvas coords."""
    return p["x"] + p["w"] / 2, p["y"] + p["h"]


def pct(values, q):
    if not values:
        return 0
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))]


def report(rows, names, poses):
    ts = [r["t"] for r in rows]
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    dur_s = (ts[-1] - ts[0]) / 1000 if len(ts) > 1 else 0
    print(f"frames: {len(rows)} over {dur_s:.1f} s")
    if gaps:
        print(f"frame interval ms: mean {statistics.mean(gaps):.1f}  p95 {pct(gaps, .95)}  "
              f"max {max(gaps)}  >50ms: {sum(g > 50 for g in gaps)}")
    fus = [r["frame_us"] for r in rows if r["frame_us"] is not None]
    if fus:
        print(f"render us: mean {statistics.mean(fus):.0f}  p95 {pct(fus, .95)}  max {max(fus)}")

    # Pose segments: runs of identical pose.
    segs = []  # (start_t, end_t, pose, reaction)
    for r in rows:
        if segs and segs[-1][2] == r["pose"]:
            segs[-1][1] = r["t"]
        else:
            if segs:
                segs[-1][1] = r["t"]
            segs.append([r["t"], r["t"], r["pose"], r["reaction"]])
    holds = [e - s for s, e, _, _ in segs[:-1]]
    print(f"pose changes: {len(segs) - 1}  ({(len(segs) - 1) / max(dur_s, 1e-9):.1f}/s)")
    if holds:
        print(f"hold ms: p10 {pct(holds, .10)}  median {pct(holds, .5)}  p90 {pct(holds, .90)}")
    flashes = [(s, names[p], rx) for (s, e, p, rx) in segs[1:-1] if e - s < FLASH_MS]
    print(f"flickers (< {FLASH_MS} ms): {len(flashes)}")

    jumps = []
    for (s0, _, p0, _), (s1, _, p1, rx) in zip(segs, segs[1:]):
        (x0, b0), (x1, b1) = anchor(poses[p0]), anchor(poses[p1])
        d = max(abs(x1 - x0), abs(b1 - b0))
        if d >= SNAP_PX:
            jumps.append((d, s1, names[p0], names[p1], rx))
    print(f"jumps (anchor shift >= {SNAP_PX} px): {len(jumps)}")
    for d, t, a, b, rx in sorted(jumps, reverse=True)[:8]:
        print(f"  {t:>6} ms  {a} -> {b}  {d:.0f}px  ({rx})")

    print("timeline:")
    prev_mood, prev_rx = None, None
    for r in rows:
        if r["mood"] != prev_mood:
            print(f"  {r['t']:>6} ms  mood {MOODS[r['mood']]}  energy {r['energy']}")
            prev_mood = r["mood"]
        if r["reaction"] != prev_rx:
            if r["reaction"] != "-":
                print(f"  {r['t']:>6} ms    reaction {r['reaction']}")
            prev_rx = r["reaction"]


def filmstrip(rows, poses, t0, t1, scale, out):
    sel = [r for r in rows if t0 <= r["t"] <= t1][:72]
    if not sel:
        sys.exit(f"no frames between {t0} and {t1} ms")
    cols = 12
    w, h = SCREEN_W * scale, SCREEN_H * scale + 12
    sheet = Image.new("RGB", (cols * w, ((len(sel) + cols - 1) // cols) * h), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    for i, r in enumerate(sel):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(render(r, poses).resize((SCREEN_W * scale, SCREEN_H * scale), Image.NEAREST), (x, y + 12))
        d.text((x + 2, y), f"{r['t']} p{r['pose']} {r['reaction']}", fill=WHITE)
    sheet.save(out)
    print(f"wrote {out} ({len(sel)} frames)")


def gif(rows, poses, scale, out):
    frames = [render(r, poses).resize((SCREEN_W * scale, SCREEN_H * scale), Image.NEAREST) for r in rows]
    durs = [max(20, b["t"] - a["t"]) for a, b in zip(rows, rows[1:])] + [33]
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0)
    print(f"wrote {out} ({len(frames)} frames)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline")
    ap.add_argument("--gif")
    ap.add_argument("--strip")
    ap.add_argument("--from", dest="t0", type=int, default=0)
    ap.add_argument("--to", dest="t1", type=int, default=10**9)
    ap.add_argument("--scale", type=int, default=2)
    a = ap.parse_args()
    names, poses = load_poses()
    rows = load_rows(a.timeline)
    report(rows, names, poses)
    if a.strip:
        filmstrip(rows, poses, a.t0, a.t1, a.scale, a.strip)
    if a.gif:
        gif(rows, poses, a.scale, a.gif)


if __name__ == "__main__":
    main()
