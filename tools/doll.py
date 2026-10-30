#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Paper-doll compositor (Python mirror of the device compositor) and preview.

Usage:  uv run tools/doll.py <doll_dir> [--sheet out.png]

<doll_dir> holds parts.json (from art/blender/<char>_doll.py) and inked part
images in poses/. A DollPose is a dict of continuous values; compose() picks
each part's nearest image and stacks them using the attachment points.
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

SCREEN_W, SCREEN_H = 160, 128

DEFAULT_POSE = {"flapL": 3.0, "flapR": 3.0}   # every other channel defaults to 0


class Doll:
    def __init__(self, doll_dir):
        self.dir = Path(doll_dir)
        meta = json.loads((self.dir / "parts.json").read_text())
        self.canvas = meta["canvas"]
        self.parts = {p["name"]: p for p in meta["parts"]}
        self.order = meta["draw_order"]
        self.channels = meta["channels"]
        self.cache = {}

    def image(self, part, idx):
        key = (part, idx)
        if key not in self.cache:
            self.cache[key] = Image.open(self.dir / "poses" / self.parts[part]["images"][idx]["file"]).convert("RGBA")
        return self.cache[key]

    def index(self, part, values):
        """Row-major index of the nearest image for these axis values."""
        idx = 0
        for ax, v in zip(self.parts[part]["axes"], values):
            vals = ax["values"]
            i = min(range(len(vals)), key=lambda k: (abs(vals[k] - v), k))
            idx = idx * len(vals) + i
        return idx

    def layout(self, pose):
        """{part: (image index, dx, dy)}: dx/dy shift the full-canvas image."""
        p = {c: 0.0 for c in self.channels} | DEFAULT_POSE | pose
        idx = {name: self.index(name, [sum(p[c] for c in ax["sources"]) for ax in part["axes"]])
               for name, part in self.parts.items()}
        delta = {}

        def place(name):
            if name in delta:
                return delta[name]
            part = self.parts[name]
            img = part["images"][idx[name]]
            if part["parent"] is None:          # the ground: rest pivot, lifted by the hop
                rest = part["images"][0]["pivot"]
                d = (rest[0] - img["pivot"][0], rest[1] - img["pivot"][1] - p["hop"])
            else:
                parent = part["parent"]
                pd = place(parent)
                anchor = self.parts[parent]["images"][idx[parent]]["anchors"][name]
                d = (anchor[0] + pd[0] - img["pivot"][0], anchor[1] + pd[1] - img["pivot"][1])
            delta[name] = d
            return d

        return {name: (idx[name], *place(name)) for name in self.order}

    def compose(self, pose, background=(236, 230, 218), sun=(223, 165, 143)):
        screen = Image.new("RGBA", (SCREEN_W, SCREEN_H), (*background, 255))
        if sun:
            ImageDraw.Draw(screen).ellipse([80 - 36, 46 - 36, 80 + 36, 46 + 36], fill=sun)
        ox, oy = (SCREEN_W - self.canvas[0]) // 2, SCREEN_H - self.canvas[1]
        for name, (i, dx, dy) in self.layout(pose).items():
            screen.alpha_composite(self.image(name, i), (ox + round(dx), oy + round(dy)))
        return screen


SAMPLES = [
    ("rest", {}),
    ("lean fwd", {"lean": 18}),
    ("lean back", {"lean": -18, "pitch": -10}),
    ("squash", {"squash": 2, "legs": 1}),
    ("hop", {"hop": 14, "legs": 3, "squash": -1, "flapL": 160, "flapR": 160}),
    ("look L", {"look": -30, "pitch": 6}),
    ("look R", {"look": 30, "crest": -30}),
    ("sing", {"pitch": -24, "jaw": 34, "crest": -36, "eyes": 1, "flapL": 30, "flapR": 30}),
    ("startle", {"lean": -12, "eyes": -1, "crest": -40, "jaw": 28, "flapL": 150, "flapR": 150}),
    ("asleep", {"squash": 3, "legs": 2, "pitch": 24, "eyes": 2, "crest": 45, "tail": 12}),
    ("nod", {"pitch": 18, "lean": 6, "tail": -10}),
    ("flap mid", {"flapL": 88, "flapR": 88, "hop": 6}),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doll_dir")
    ap.add_argument("--sheet", default=".pio/doll_sheet.png")
    a = ap.parse_args()
    doll = Doll(a.doll_dir)
    scale, cols = 3, 4
    w, h = SCREEN_W * scale, SCREEN_H * scale + 14
    sheet = Image.new("RGB", (cols * w, ((len(SAMPLES) + cols - 1) // cols) * h), (60, 60, 60))
    d = ImageDraw.Draw(sheet)
    for i, (label, pose) in enumerate(SAMPLES):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(doll.compose(pose).resize((SCREEN_W * scale, SCREEN_H * scale), Image.NEAREST), (x, y + 14))
        d.text((x + 4, y + 1), label, fill=(255, 255, 255))
    sheet.save(a.sheet)
    print(f"sheet -> {a.sheet}")


if __name__ == "__main__":
    main()
