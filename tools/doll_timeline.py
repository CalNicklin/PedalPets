#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy"]
# ///
"""Redraw a paper-doll timeline (simulator or device telemetry) and report
how smooth it is.

Usage:
  uv run tools/doll_timeline.py timeline.csv <doll_dir> [--gif out.gif]
         [--strip out.png --from MS --to MS] [--scale N] [--panel]

--panel shows frames as the TN panel displays them (slow pixels ghost; see
tools/panel.py) and reports how much of each frame is ghosted.
"""

import argparse
import csv
import json
import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from panel import GHOST_LEVEL, Panel, ghost_pixels

SCREEN_W, SCREEN_H = 160, 128
MOODS = ["Asleep", "Curious", "IntoIt", "Hyped"]
BG, SUN = (236, 230, 218), (223, 165, 143)
JUMP_PX = 4      # a part's pivot moving this far in one frame reads as a jump


class Art:
    def __init__(self, doll_dir, scene_dir=None):
        self.backdrop, self.leaves, self.crowd = None, [], []
        if scene_dir:
            sd = Path(scene_dir)
            self.backdrop = Image.open(sd / "backdrop.png").convert("RGBA")
            n = json.loads((sd / "scene.json").read_text())["leaves"]
            self.leaves = [Image.open(sd / "leaves" / f"{i}.png").convert("RGBA") for i in range(n)]
            nc = json.loads((sd / "scene.json").read_text()).get("crowd", 0)
            self.crowd = [Image.open(sd / "crowd" / f"{i}.png").convert("RGBA") for i in range(nc)]
        d = Path(doll_dir)
        meta = json.loads((d / "parts.json").read_text())
        self.canvas = meta["canvas"]
        self.order = [next(i for i, p in enumerate(meta["parts"]) if p["name"] == n) for n in meta["draw_order"]]
        self.part_names = [p["name"] for p in meta["parts"]]
        self.crops, self.pivots, self.labels = [], [], []
        for p in meta["parts"]:
            for img in p["images"]:
                im = Image.open(d / "poses" / img["file"]).convert("RGBA")
                box = im.getchannel("A").getbbox() or (0, 0, 1, 1)
                self.crops.append(im.crop(box))
                self.flipped = getattr(self, "flipped", [])
                self.flipped.append(ImageOps.mirror(im.crop(box)))
                self.pivots.append((img["pivot"][0] - box[0], img["pivot"][1] - box[1]))
                self.labels.append(f"{p['name']}{img['values']}")
        self.ox, self.oy = (SCREEN_W - self.canvas[0]) // 2, SCREEN_H - self.canvas[1]
        self.marks = []
        mj = d / "marks" / "marks.json"
        if mj.exists():
            self.marks = [Image.open(d / "marks" / f"{n}.png").convert("RGBA")
                          for n in json.loads(mj.read_text())["images"]]

    def draw_leaves(self, img, row, front):
        for s, x, y, f in row["leaves"]:
            if s < 0 or f != front or not self.leaves:
                continue
            sp = self.leaves[s]
            img.alpha_composite(sp, (x - sp.width // 2, y - sp.height + 1))

    def render(self, row):
        if self.backdrop:
            img = self.backdrop.copy()
        else:
            img = Image.new("RGBA", (SCREEN_W, SCREEN_H), (*BG, 255))
            ImageDraw.Draw(img).ellipse([80 - 36, 46 - 36, 80 + 36, 46 + 36], fill=SUN)
        for sp, x, y, f in row.get("crowd", []):
            if sp >= 0 and self.crowd:
                im = self.crowd[sp]
                img.alpha_composite(ImageOps.mirror(im) if f else im, (x, y))
        self.draw_leaves(img, row, 0)
        crops = self.flipped if row["flip"] else self.crops
        for i in self.order:
            n, x, y = row["parts"][i]
            img.alpha_composite(crops[n], (self.ox + x, self.oy + y))
        self.draw_leaves(img, row, 1)
        for n, x, y in row["marks"]:
            img.alpha_composite(self.marks[n], (self.ox + x, self.oy + y))
        if row.get("say") and row["say"] != "-":
            self.draw_bubble(img, row)
        return img

    def draw_bubble(self, img, row):
        """As the board draws it (renderer_tft.cpp drawCaption): a scalloped white thought cloud,
        top left, slanted capitals, a trail of circles towards the head."""
        from PIL import ImageFont
        words, lines = row["say"].replace(";", ",").split(), [""]
        for w in words:
            if len(lines[-1]) + len(w) + (1 if lines[-1] else 0) <= 24:
                lines[-1] = (lines[-1] + " " + w).strip()
            elif len(lines) < 2:
                lines.append(w)
        lines = [l.upper() for l in lines]
        w, h = max(len(l) for l in lines) * 6 + 10, len(lines) * 9 + 6
        x, y = 4, 4
        d = ImageDraw.Draw(img)
        ink, white = (32, 24, 32), (255, 255, 255)
        def edge(col, r):
            pts = [(px, y) for px in range(x + 3, x + w - 2, 6)] + [(px, y + h - 1) for px in range(x + 3, x + w - 2, 6)]
            pts += [(x, py) for py in range(y + 3, y + h - 3, 5)] + [(x + w - 1, py) for py in range(y + 3, y + h - 3, 5)]
            for px, py in pts:
                d.ellipse([px - r, py - r, px + r, py + r], fill=col)
        edge(ink, 3); edge(white, 2)
        d.rectangle([x, y, x + w - 1, y + h - 1], fill=white)
        font = ImageFont.load_default(size=8)
        for i, l in enumerate(lines):
            layer = Image.new("L", (len(l) * 6 + 4, 9), 0)
            ImageDraw.Draw(layer).text((0, -1), l, fill=255, font=font)
            layer = layer.transform(layer.size, Image.AFFINE, (1, 0.3, -2.4, 0, 1, 0), resample=Image.NEAREST)
            img.paste(ink, (x + 4, y + 3 + i * 9), layer)
        k = self.part_names.index("skull") if "skull" in self.part_names else self.part_names.index("head")
        n, px, py = row["parts"][k]
        hx, hy = self.ox + px + self.crops[n].width // 2, self.oy + py
        sx, sy = x + w - 6, y + h + 4
        dx, dy = hx - sx, hy - sy
        dist = (dx * dx + dy * dy) ** 0.5
        if dist >= 12:
            dx, dy, along = dx / dist, dy / dist, 0
            for r in (3, 2, 1):
                cx, cy = sx + int(dx * along), sy + int(dy * along)
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=white, outline=ink)
                along += 2 * r + 4

    def mask(self, row):
        m = Image.new("L", (SCREEN_W, SCREEN_H), 0)
        for i in self.order:
            n, x, y = row["parts"][i]
            crop = (self.flipped if row["flip"] else self.crops)[n]
            m.paste(255, (self.ox + x, self.oy + y), crop.getchannel("A"))
        return m


def load(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            if None in r.values():
                continue                 # a line cut short over serial
            n = sum(1 for k in r if k.startswith("p") and k.endswith("_img"))
            nm = sum(1 for k in r if k.startswith("m") and k.endswith("_img"))
            nl = sum(1 for k in r if k.startswith("l") and k.endswith("_s"))
            nc = sum(1 for k in r if k.startswith("c") and k.endswith("_s"))
            rows.append({"t": int(r["t_ms"]), "mood": int(r["mood"]), "energy": r["energy"],
                         "reaction": r["reaction"], "frame_us": int(r["frame_us"]) if r["frame_us"] else None,
                         "flip": r.get("flip") == "1",
                         "parts": [(int(r[f"p{i}_img"]), int(r[f"p{i}_x"]), int(r[f"p{i}_y"])) for i in range(n)],
                         "marks": [(int(r[f"m{i}_img"]), int(r[f"m{i}_x"]), int(r[f"m{i}_y"]))
                                   for i in range(nm) if int(r[f"m{i}_img"]) >= 0],
                         "leaves": [(int(r[f"l{i}_s"]), int(r[f"l{i}_x"]), int(r[f"l{i}_y"]), int(r[f"l{i}_f"]))
                                    for i in range(nl)],
                         "crowd": [(int(r[f"c{i}_s"]), int(r[f"c{i}_x"]), int(r[f"c{i}_y"]), int(r[f"c{i}_f"]))
                                   for i in range(nc)],
                         "say": r.get("say", "-")})
    return rows


def pct(v, q):
    s = sorted(v)
    return s[min(len(s) - 1, int(q * len(s)))] if s else 0


def report(rows, art, panel=False):
    ts = [r["t"] for r in rows]
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    print(f"frames: {len(rows)} over {(ts[-1] - ts[0]) / 1000:.1f} s")
    print(f"frame interval ms: mean {statistics.mean(gaps):.1f}  p95 {pct(gaps, .95)}  max {max(gaps)}  "
          f">50ms: {sum(g > 50 for g in gaps)}")
    fus = [r["frame_us"] for r in rows if r["frame_us"] is not None]
    if fus:
        print(f"render us: mean {statistics.mean(fus):.0f}  p95 {pct(fus, .95)}  max {max(fus)}")

    # Part pivots on screen, relative to the ground part (a hop moves the whole
    # body together). Fast motion moves a part a lot every frame, steadily; a
    # glitch is a sudden change in that velocity: a part lurching out of line
    # for a frame, or an image step pulling it. So measure the jerk.
    def screen_pivot(r, n, x, y):
        px, py = art.pivots[n]
        if r["flip"]:
            px = art.crops[n].width - px
        return x + px, y + py

    def pivot(r, i):
        gx, gy = screen_pivot(r, *r["parts"][0])
        px, py = screen_pivot(r, *r["parts"][i])
        return px - gx, py - gy

    jerks, fastest = [], 0
    for a, b, c in zip(rows, rows[1:], rows[2:]):
        if not a["flip"] == b["flip"] == c["flip"]:
            continue                     # turning round is a deliberate mirror, not a glitch
        for i in range(1, len(a["parts"])):
            pa, pb, pc = pivot(a, i), pivot(b, i), pivot(c, i)
            v1 = (pb[0] - pa[0], pb[1] - pa[1])
            v2 = (pc[0] - pb[0], pc[1] - pb[1])
            fastest = max(fastest, abs(v2[0]), abs(v2[1]))
            j = max(abs(v2[0] - v1[0]), abs(v2[1] - v1[1]))
            if j >= JUMP_PX:
                jerks.append((j, c["t"], art.part_names[i], b["reaction"], c["reaction"]))
    print(f"glitches (part velocity changes >= {JUMP_PX}px/frame at once): {len(jerks)}  "
          f"(fastest part motion {fastest:.0f}px/frame)")
    for d, t, part, ra, rb in sorted(jerks, reverse=True)[:6]:
        print(f"  {t:>6} ms  {part} {d:.0f}px  ({ra} -> {rb})")

    # Silhouette change between consecutive frames.
    changes, prev = [], None
    for r in rows:
        m = art.mask(r).tobytes()
        if prev is not None:
            union = sum(1 for x, y in zip(prev, m) if x or y)
            diff = sum(1 for x, y in zip(prev, m) if (x > 127) != (y > 127))
            changes.append((diff / max(union, 1), r["t"], r["reaction"]))
        prev = m
    vals = sorted(c[0] for c in changes)
    print(f"silhouette change per frame: median {100 * pct(vals, .5):.0f}%  p95 {100 * pct(vals, .95):.0f}%  "
          f"max {100 * vals[-1]:.0f}%")
    for v, t, rx in sorted(changes, reverse=True)[:6]:
        print(f"  {t:>6} ms  {100 * v:.0f}%  ({rx})")

    if panel:
        p, ghosts = Panel(), []
        for r in rows:
            drawn = art.render(r)
            ghosts.append((ghost_pixels(drawn, p.show(drawn)), r["t"], r["reaction"]))
        vals = sorted(g[0] for g in ghosts)
        print(f"panel ghosting (px off by >{GHOST_LEVEL}/255): median {pct(vals, .5)}  p95 {pct(vals, .95)}  max {vals[-1]}  "
              f"mean {statistics.mean(vals):.0f}")
        for g, t, rx in sorted(ghosts, reverse=True)[:6]:
            print(f"  {t:>6} ms  {g}px  ({rx})")

    print("timeline:")
    pm, pr = None, None
    for r in rows:
        if r["mood"] != pm:
            print(f"  {r['t']:>6} ms  mood {MOODS[r['mood']]}  energy {r['energy']}")
            pm = r["mood"]
        if r["reaction"] != pr:
            if r["reaction"] != "-":
                print(f"  {r['t']:>6} ms    reaction {r['reaction']}")
            pr = r["reaction"]


def displayed(rows, sel, art, panel):
    """Frames for `sel` as drawn, or as the panel shows them (warmed up on the frames before)."""
    if not panel:
        return [art.render(r) for r in sel]
    p, first = Panel(), rows.index(sel[0])
    for r in rows[max(0, first - 3):first]:
        p.show(art.render(r))
    return [p.show(art.render(r)) for r in sel]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline")
    ap.add_argument("doll_dir")
    ap.add_argument("--scene", help="scene dir from tools/build_scene.py (e.g. art/scenes/forest)")
    ap.add_argument("--gif")
    ap.add_argument("--strip")
    ap.add_argument("--from", dest="t0", type=int, default=0)
    ap.add_argument("--to", dest="t1", type=int, default=10**9)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--panel", action="store_true", help="simulate the TN panel's ghosting")
    a = ap.parse_args()
    art = Art(a.doll_dir, a.scene)
    rows = load(a.timeline)
    if not a.quiet:
        report(rows, art, a.panel)
    s = a.scale
    if a.strip:
        sel = [r for r in rows if a.t0 <= r["t"] <= a.t1][:72]
        shown = displayed(rows, sel, art, a.panel)
        cols = 12
        w, h = SCREEN_W * s, SCREEN_H * s + 12
        sheet = Image.new("RGB", (cols * w, ((len(sel) + cols - 1) // cols) * h), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        for i, r in enumerate(sel):
            x, y = (i % cols) * w, (i // cols) * h
            sheet.paste(shown[i].resize((SCREEN_W * s, SCREEN_H * s), Image.NEAREST), (x, y + 12))
            d.text((x + 2, y), f"{r['t']} {MOODS[r['mood']]} {r['reaction']}", fill=(255, 255, 255))
        sheet.save(a.strip)
        print(f"wrote {a.strip} ({len(sel)} frames)")
    if a.gif:
        sel = [r for r in rows if a.t0 <= r["t"] <= a.t1]
        frames = [f.resize((SCREEN_W * s, SCREEN_H * s), Image.NEAREST).convert("RGB")
                  for f in displayed(rows, sel, art, a.panel)]
        durs = [max(20, b["t"] - a_["t"]) for a_, b in zip(sel, sel[1:])] + [30]
        frames[0].save(a.gif, save_all=True, append_images=frames[1:], duration=durs, loop=0)
        print(f"wrote {a.gif} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
