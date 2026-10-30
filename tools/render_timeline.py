#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Re-render a frame timeline (from the simulator or device telemetry) and
report how smooth it is.

Usage:
  uv run tools/render_timeline.py timeline.csv [--manifest art/x.toml] [--gif out.gif]
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

SCREEN_W, SCREEN_H = ba.SCREEN_W, ba.SCREEN_H
EYES = ["Auto", "Open", "Blink", "LookL", "LookR", "Wide", "HappyClosed"]
MOODS = ["Asleep", "Curious", "IntoIt", "Hyped"]
WHITE = (255, 255, 255)
SNAP_PX = 6          # pose-to-pose feet shift that reads as a jump
FEET_ROWS = 12       # bottom rows of a pose used to locate its feet


SUN = (SCREEN_W // 2, 46, 36)   # mirrors renderer_tft.cpp
BG = {}


def load_poses(manifest):
    """Pose names and images; each pose's x/y is made screen-relative,
    mirroring renderer_tft.cpp (canvas centred, bottom-aligned)."""
    m = tomllib.loads(Path(manifest).read_text())
    BG.update(ba.background(m))
    lay = ba.layout(m)
    cx, cy = (SCREEN_W - lay["w"]) // 2, SCREEN_H - lay["h"]
    raw = ba.collect_poses(m)
    names = list(raw)
    poses = [ba.process_pose(n, raw[n], lay) for n in names]
    for p in poses:
        p["feet"] = feet_x(p)
        p["sx"], p["sy"] = cx + p["x"], cy + p["y"]
        p["sex"], p["sey"] = cx + p["ex"], cy + p["ey"]
    return names, poses


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
    img = Image.new("RGB", (SCREEN_W, SCREEN_H), BG["color"])
    if BG["sun"]:
        x, y, r = SUN
        ImageDraw.Draw(img).ellipse([x - r, y - r, x + r, y + r], fill=BG["sun"])
    p = poses[row["pose"]]
    img.paste(p["rgba"], (p["sx"], p["sy"]), p["rgba"])
    if p["ex"] != -1:
        draw_eyes(ImageDraw.Draw(img), p["sex"], p["sey"], row["eye"])
    return img


def feet_x(p):
    """Horizontal centre of the pose's lowest rows (its feet), in canvas coords.
    Ignores staffs and spell effects that swing the bounding box around."""
    img = p["image"]
    strip = img.crop((0, max(0, img.height - FEET_ROWS), img.width, img.height)).convert("L")
    box = strip.point(lambda v: 255 if v > 8 else 0).getbbox()
    return p["x"] + ((box[0] + box[2]) / 2 if box else img.width / 2)


def anchor(p):
    """Feet centre and bottom of the pose's drawn pixels, in canvas coords."""
    return p["feet"], p["y"] + p["h"]


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

    # Judder: inside a run of the same animation (same reaction, or idle in the
    # same mood) the cadence should be steady; a hold that differs from the one
    # before it by a frame or more reads as a stutter.
    mood_at = {r["t"]: r["mood"] for r in rows}
    pairs = judder = 0
    for (s0, e0, _, rx0), (s1, e1, _, rx1), (s2, _, _, rx2) in zip(segs, segs[1:], segs[2:]):
        same = rx0 == rx1 == rx2 and (rx1 != "-" or mood_at[s0] == mood_at[s1] == mood_at[s2])
        if not same:
            continue
        pairs += 1
        judder += abs((e1 - s1) - (e0 - s0)) >= 25
    print(f"cadence judder: {judder}/{pairs} consecutive holds uneven"
          f" ({100 * judder / max(pairs, 1):.0f}%)")

    # Glitch: a pose on screen for a single frame at a boundary (reaction or
    # mood change), i.e. something that flashes up and vanishes.
    # (An idle pose cut short by a reaction starting is fine: reactions must be instant.)
    # Only meaningful where the neighbours are held longer (on-ones art is all single frames).
    glitches = [(s, names[p]) for (s, e, p, rx), prev, nxt in zip(segs[1:-1], segs, segs[2:])
                if e - s <= 40 and prev[1] - prev[0] > 60 and nxt[1] - nxt[0] > 60
                and (prev[3] != rx or nxt[3] != rx) and not (rx == "-" and nxt[3] != "-")]
    print(f"single-frame glitches at boundaries: {len(glitches)}")
    for t, n in glitches[:5]:
        print(f"  {t:>6} ms  {n}")

    jumps = []
    for (s0, _, p0, _), (s1, _, p1, rx) in zip(segs, segs[1:]):
        (x0, b0), (x1, b1) = anchor(poses[p0]), anchor(poses[p1])
        d = max(abs(x1 - x0), abs(b1 - b0))
        if d >= SNAP_PX:
            jumps.append((d, s1, names[p0], names[p1], rx))
    print(f"jumps (anchor shift >= {SNAP_PX} px): {len(jumps)}")
    for d, t, a, b, rx in sorted(jumps, reverse=True)[:8]:
        print(f"  {t:>6} ms  {a} -> {b}  {d:.0f}px  ({rx})")

    pops(rows, names, poses)

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


def pops(rows, names, poses):
    """Share of character pixels that change between consecutive frames.
    Smooth motion changes a little each frame; a cut changes a lot at once."""
    def mask(pose):
        p = poses[pose]
        m = Image.new("L", (SCREEN_W, SCREEN_H), 0)
        m.paste(p["rgba"].getchannel("A"), (p["sx"], p["sy"]))
        return m

    cache, out = {}, []
    for a, b in zip(rows, rows[1:]):
        if a["pose"] == b["pose"]:
            continue
        key = (a["pose"], b["pose"])
        if key not in cache:
            ma, mb = mask(a["pose"]), mask(b["pose"])
            union = Image.eval(Image.merge("RGB", (ma, mb, ma)).convert("L"), lambda v: v).getbbox()
            ia, ib = ma.tobytes(), mb.tobytes()
            both = sum(1 for x, y in zip(ia, ib) if x or y)
            diff = sum(1 for x, y in zip(ia, ib) if (x > 127) != (y > 127))
            cache[key] = diff / max(both, 1)
        boundary = a["reaction"] != b["reaction"] or a["mood"] != b["mood"]
        out.append((cache[key], b["t"], names[a["pose"]], names[b["pose"]],
                    f"{a['reaction']} -> {b['reaction']}" if boundary else b["reaction"], boundary))
    for label, sel in (("within animations", [o for o in out if not o[5]]),
                       ("at boundaries (reaction start/end, mood change)", [o for o in out if o[5]])):
        if not sel:
            continue
        vals = sorted(o[0] for o in sel)
        print(f"silhouette change {label}: n={len(sel)} median {100 * vals[len(vals) // 2]:.0f}%  "
              f"p95 {100 * vals[int(.95 * len(vals))]:.0f}%  max {100 * vals[-1]:.0f}%")
        for v, t, a, b, rx, _ in sorted(sel, reverse=True)[:6]:
            print(f"  {t:>6} ms  {a} -> {b}  {100 * v:.0f}%  ({rx})")


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
    ap.add_argument("--manifest", default=str(ba.MANIFEST))
    ap.add_argument("--gif")
    ap.add_argument("--strip")
    ap.add_argument("--from", dest="t0", type=int, default=0)
    ap.add_argument("--to", dest="t1", type=int, default=10**9)
    ap.add_argument("--scale", type=int, default=2)
    a = ap.parse_args()
    names, poses = load_poses(a.manifest)
    rows = load_rows(a.timeline)
    report(rows, names, poses)
    if a.strip:
        filmstrip(rows, poses, a.t0, a.t1, a.scale, a.strip)
    if a.gif:
        gif(rows, poses, a.scale, a.gif)


if __name__ == "__main__":
    main()
