#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Turn flat-colour Blender renders into palette "ink" frames.

Usage:  uv run tools/ink.py <raw_dir> <out_dir> [--ss 2]

Each raw RGBA render (supersampled) is snapped to the material colours,
downsampled by majority vote, then given 1 px ink lines: around the
silhouette and wherever two non-ink colours meet. Output PNGs use exactly the
palette below plus transparency.
"""

import argparse
from collections import Counter
from pathlib import Path

from PIL import Image

# Material colours as rendered by art/blender/pet.py -> output palette colour.
PALETTE = {
    "ink":   ((5, 5, 5),       (24, 22, 22)),
    "skin":  ((179, 179, 179), (150, 146, 140)),
    "red":   ((231, 15, 15),   (200, 32, 32)),
    "white": ((255, 255, 255), (250, 248, 242)),
}
NAMES = list(PALETTE)
INK = NAMES.index("ink")
CLEAR = -1


def classify(px):
    r, g, b, a = px
    if a < 128:
        return CLEAR
    return min(range(len(NAMES)), key=lambda i: sum((c - k) ** 2 for c, k in zip((r, g, b), PALETTE[NAMES[i]][0])))


def ink_frame(raw, ss):
    w, h = raw.width // ss, raw.height // ss
    data = raw.tobytes()
    cache = {}
    src = []
    for i in range(0, len(data), 4):
        px = tuple(data[i:i + 4])
        if px not in cache:
            cache[px] = classify(px)
        src.append(cache[px])
    rw = raw.width
    grid = [[CLEAR] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            votes = Counter(src[(y * ss + dy) * rw + x * ss + dx] for dy in range(ss) for dx in range(ss))
            opaque = [(n, c) for c, n in votes.items() if c != CLEAR]
            if sum(n for n, _ in opaque) * 2 >= ss * ss:
                grid[y][x] = max(opaque)[1]

    def at(x, y):
        return grid[y][x] if 0 <= x < w and 0 <= y < h else CLEAR

    out = [row[:] for row in grid]
    for y in range(h):
        for x in range(w):
            c = grid[y][x]
            if c == CLEAR or c == INK:
                continue
            nbrs = (at(x - 1, y), at(x + 1, y), at(x, y - 1), at(x, y + 1))
            if CLEAR in nbrs:
                out[y][x] = INK                       # silhouette
            elif any(n not in (c, INK) and n > c for n in nbrs):
                out[y][x] = INK                       # boundary between two fills (one side only)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.putdata([(0, 0, 0, 0) if c == CLEAR else (*PALETTE[NAMES[c]][1], 255) for row in out for c in row])
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--ss", type=int, default=2)
    ap.add_argument("--sheet", help="also write a contact sheet of the inked frames here")
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(Path(a.raw_dir).glob("*.png"))
    for f in files:
        ink_frame(Image.open(f).convert("RGBA"), a.ss).save(out / f.name)
    print(f"ink: {len(files)} frames -> {out}")
    if a.sheet:
        contact_sheet([out / f.name for f in files], a.sheet)


def contact_sheet(paths, dest, cols=12, scale=2):
    """Frames on the screen background, at the device's on-screen position."""
    w, h = 160 * scale, 128 * scale + 10
    sheet = Image.new("RGB", (cols * w, ((len(paths) + cols - 1) // cols) * h), (60, 60, 60))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(paths):
        frame = Image.new("RGBA", (160, 128), (236, 230, 218, 255))
        ImageDraw.Draw(frame).ellipse([80 - 36, 46 - 36, 80 + 36, 46 + 36], fill=(223, 165, 143))
        frame.alpha_composite(Image.open(p).convert("RGBA"), (32, 16))
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(frame.resize((160 * scale, 128 * scale), Image.NEAREST), (x, y + 10))
        d.text((x + 2, y - 1), p.stem, fill=(255, 255, 255))
    sheet.save(dest)
    print(f"sheet -> {dest}")


if __name__ == "__main__":
    main()
