"""Graveyard at dusk: a backdrop for the paper-doll pets (spooky, but cute).

Same rules as forest.py: flat colour with soft (non-black) outlines so the
pet's ink lines stay on top, the middle kept open, feet at y = 124. Shares the
forest's drawing helpers and autumn leaves.

  draw() -> RGB backdrop     leaf_sprites() -> list of RGBA leaf images
"""
import os
import random
import sys

from PIL import ImageDraw, Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forest import H, W, circle, layer, rect  # noqa: E402,F401
from forest import LEAF_COLOURS, ROTATIONS, leaf_sprites  # noqa: E402,F401

GROUND_Y = 113
FEET_Y = 124

C = {
    "sky_top":    (54, 44, 88),
    "sky_2":      (74, 58, 110),
    "sky_mid":    (98, 74, 124),
    "sky_low":    (136, 92, 130),
    "sky_glow":   (176, 116, 136),
    "star":       (232, 226, 250),
    "moon":       (246, 234, 196),
    "moon_dk":    (226, 210, 168),
    "halo":       (122, 100, 150),
    "cloud":      (84, 66, 116),
    "far":        (66, 56, 94),
    "hills":      (74, 64, 102),
    "hills2":     (60, 54, 86),
    "fence":      (44, 38, 62),
    "tree":       (52, 42, 60),
    "tree_line":  (34, 28, 42),
    "stone":      (150, 146, 160),
    "stone_dk":   (120, 116, 134),
    "stone_line": (78, 72, 92),
    "ground":     (88, 84, 74),
    "ground_dk":  (72, 68, 60),
    "ground_line": (56, 52, 46),
    "grass":      (92, 112, 78),
    "pumpkin":    (226, 124, 44),
    "pumpkin_ln": (150, 70, 26),
    "stalk":      (96, 120, 64),
    "lamp":       (255, 214, 120),
    "firefly":    (220, 246, 150),
}


def headstone(x, top, w, h):
    """A rounded headstone standing on the ground line."""
    r = w // 2
    return [circle(x + r, top + r, r), rect(x, top + r, x + w - 1, top + h)]


def limb(points, r0, r1):
    """A tapering limb along a polyline: radius r0 at the start to r1 at the end."""
    def shape(d):
        segs = list(zip(points, points[1:]))
        total = sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in segs) or 1
        done = 0.0
        for a, b in segs:
            length = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
            steps = max(1, int(length * 2))
            for k in range(steps + 1):
                u = k / steps
                x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
                r = r0 + (r1 - r0) * (done + length * u) / total
                d.ellipse([x - r, y - r, x + r, y + r], fill=255)
            done += length
    return shape


def dither(d, y0, y1, upper, lower):
    """Blend two sky bands over rows y0..y1 with an ordered (checker -> sparse) dither."""
    rows = y1 - y0
    for i, y in enumerate(range(y0, y1)):
        u = (i + 1) / (rows + 1)                       # share of the lower colour
        for x in range(W):
            bayer = ((x % 2) * 2 + (y % 2) * 3) % 4 / 4 + 0.125
            d.point((x, y), fill=lower if bayer < u else upper)


def draw(seed=11):
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), C["sky_top"])
    d = ImageDraw.Draw(img)

    # Dusk: flat bands blended with pixel dithering, a glow low on the horizon.
    bands = [(0, C["sky_top"]), (22, C["sky_2"]), (44, C["sky_mid"]), (66, C["sky_low"]), (82, C["sky_glow"])]
    for (y0, col), nxt in zip(bands, bands[1:] + [(H, None)]):
        d.rectangle([0, y0, W - 1, nxt[0] - 1], fill=col)
    for (y0, upper), (y1, lower) in zip(bands, bands[1:]):
        dither(d, y1 - 3, y1 + 3, upper, lower)

    # Stars in the upper sky; two brighter ones with little cross glints.
    for _ in range(18):
        x, y = rnd.randrange(W), rnd.randrange(0, 40)
        if not (98 < x < 140 and y < 56):
            d.point((x, y), fill=C["star"])
    for x, y in ((58, 12), (150, 26)):
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            d.point((x + dx, y + dy), fill=C["star"])

    # The moon: a soft halo, craters, and a thin cloud drifting across it.
    layer(img, [circle(118, 34, 22)], C["halo"])
    layer(img, [circle(118, 34, 18)], C["moon"])
    layer(img, [circle(112, 30, 4), circle(124, 40, 3), circle(121, 27, 2)], C["moon_dk"])
    layer(img, [lambda dd: dd.rounded_rectangle([90, 40, 134, 43], 2, fill=255),
                lambda dd: dd.rounded_rectangle([104, 45, 150, 47], 1, fill=255)], C["cloud"])

    # Far off: hills, a little chapel and a few pines on the horizon.
    layer(img, [circle(x, 112, r) for x, r in ((8, 30), (54, 22), (96, 26), (140, 28), (172, 30))], C["hills"])
    chapel = [rect(84, 80, 96, 96), lambda dd: dd.polygon([(83, 80), (90, 73), (97, 80)], fill=255),
              rect(89, 66, 91, 74), rect(87, 68, 93, 69)]
    pines = [lambda dd, x=x, h=h: dd.polygon([(x - 4, 96), (x, 96 - h), (x + 4, 96)], fill=255)
             for x, h in ((66, 14), (72, 10), (104, 12), (110, 16))]
    layer(img, chapel + pines, C["far"])
    layer(img, [circle(x, 120, r) for x, r in ((-8, 20), (30, 16), (70, 18), (110, 14), (150, 20))], C["hills2"])

    # The iron fence across the back.
    d.line([(0, 98), (W - 1, 98)], fill=C["fence"])
    d.line([(0, 104), (W - 1, 104)], fill=C["fence"])
    for x in range(2, W, 6):
        d.line([(x, 94), (x, GROUND_Y)], fill=C["fence"])
        d.point((x, 93), fill=C["fence"])

    # A gnarled old tree on the left: flared roots, a leaning trunk, limbs that
    # taper to twigs (running off the top), and a knot hole.
    tree = [
        limb([(14, GROUND_Y + 2), (15, 80), (13, 56), (16, 34), (14, 14)], 6.5, 2.5),      # trunk
        limb([(6, GROUND_Y + 1), (11, GROUND_Y - 4)], 2.5, 3.5),                          # roots
        limb([(25, GROUND_Y + 1), (18, GROUND_Y - 5)], 2.5, 3.5),
        limb([(15, 60), (26, 50), (34, 40), (44, 36)], 3, 1),                            # long limb right
        limb([(34, 40), (38, 30), (36, 22)], 1.5, 0.6),
        limb([(14, 46), (6, 38), (1, 30)], 2.5, 1),                                      # limb left
        limb([(15, 34), (24, 22), (30, 10), (28, 0)], 2, 0.7),                           # upper right
        limb([(14, 24), (8, 12), (9, 0)], 1.6, 0.6),                                     # upper left
        limb([(24, 22), (32, 20), (38, 14)], 1, 0.5),
    ]
    layer(img, tree, C["tree"], C["tree_line"])
    layer(img, [circle(15, 70, 1.6)], C["tree_line"])                                     # knot hole
    for x0, y0, x1, y1 in ((44, 36, 48, 33), (44, 36, 47, 39), (36, 22, 39, 18), (38, 14, 41, 11), (1, 30, -1, 26)):
        d.line([(x0, y0), (x1, y1)], fill=C["tree_line"])                                # twigs

    # Headstones and a cross at the edges of the clearing.
    layer(img, headstone(124, 92, 12, 21) + headstone(140, 98, 10, 15) + headstone(26, 96, 10, 17),
          C["stone"], C["stone_line"])
    layer(img, [rect(150, 88, 153, GROUND_Y), rect(146, 92, 157, 95)], C["stone_dk"], C["stone_line"])
    for x, y in ((127, 100), (128, 103), (143, 104)):                 # carved lines
        d.line([(x, y), (x + 5, y)], fill=C["stone_line"])

    # Ground strip, specks and tufts.
    layer(img, [rect(0, GROUND_Y, W - 1, H - 1)], C["ground"])
    d.line([(0, GROUND_Y), (W - 1, GROUND_Y)], fill=C["ground_line"])
    for _ in range(40):
        d.point((rnd.randrange(W), rnd.randrange(GROUND_Y + 2, H)), fill=C["ground_dk"])
    for x in list(range(4, 36, 7)) + list(range(118, 160, 7)) + [50, 70, 98]:
        y = GROUND_Y + rnd.randrange(0, 3)
        d.line([(x, y), (x - 1, y - 3)], fill=C["grass"])
        d.line([(x + 1, y), (x + 2, y - 3)], fill=C["grass"])

    # A little pumpkin and a lantern glowing on a post.
    layer(img, [circle(38, GROUND_Y - 1, 5), circle(43, GROUND_Y - 1, 4)], C["pumpkin"], C["pumpkin_ln"])
    for x in (38, 42):                                                # ridges
        d.line([(x, GROUND_Y - 4), (x, GROUND_Y + 2)], fill=C["pumpkin_ln"])
    d.line([(40, GROUND_Y - 7), (41, GROUND_Y - 9)], fill=C["stalk"])
    d.line([(132, 70), (132, GROUND_Y)], fill=C["fence"])
    layer(img, [rect(129, 64, 135, 70)], C["lamp"], C["fence"])

    # Fireflies.
    for x, y in ((44, 60), (70, 48), (96, 66), (140, 56), (22, 70), (60, 80)):
        d.point((x, y), fill=C["firefly"])
    return img


# --- the crowd: little ghosts behind the headstones (see forest.py) ---------------
CROWD_COLOURS = {"o": (78, 72, 96), "w": (240, 238, 248), "k": (40, 34, 56), "b": (200, 196, 222),
                 "P": (236, 160, 190)}
CRITTERS = {
    "ghost": {"up": ["..oooo..",
                     ".owwwwo.",
                     "owkwwkwo",
                     "owwPPwwo",
                     "owwwwwwo",
                     "owbwwbwo",
                     "owowwowo",
                     ".o.oo.o."], "peek": 3, "arms": [(0, 2), (0, 3), (7, 2), (7, 3)]},
}
CROWD = [(130, 92, "ghost"), (145, 98, "ghost"), (31, 96, "ghost"), (152, 88, "ghost")]


def crowd_sprites():
    import forest
    return forest.crowd_sprites(CRITTERS, CROWD_COLOURS)


if __name__ == "__main__":
    draw().save(sys.argv[1] if len(sys.argv) > 1 else "graveyard.png")
