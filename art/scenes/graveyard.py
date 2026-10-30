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
    "sky_top":    (64, 52, 98),
    "sky_mid":    (98, 74, 124),
    "sky_low":    (158, 106, 132),
    "moon":       (246, 234, 196),
    "moon_dk":    (226, 210, 168),
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


def draw(seed=11):
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), C["sky_top"])
    d = ImageDraw.Draw(img)

    # Dusk in bands (flat steps, not a smooth gradient: it suits the ink style).
    for y0, col in ((34, C["sky_mid"]), (70, C["sky_low"])):
        d.rectangle([0, y0, W - 1, H - 1], fill=col)

    # Big moon, a couple of craters.
    layer(img, [circle(118, 34, 18)], C["moon"])
    layer(img, [circle(112, 30, 4), circle(124, 40, 3), circle(121, 27, 2)], C["moon_dk"])

    # Rolling hills, then an iron fence across the back.
    layer(img, [circle(x, 112, r) for x, r in ((8, 30), (54, 22), (96, 26), (140, 28), (172, 30))], C["hills"])
    layer(img, [circle(x, 120, r) for x, r in ((-8, 20), (30, 16), (70, 18), (110, 14), (150, 20))], C["hills2"])
    d.line([(0, 98), (W - 1, 98)], fill=C["fence"])
    d.line([(0, 104), (W - 1, 104)], fill=C["fence"])
    for x in range(2, W, 6):
        d.line([(x, 94), (x, GROUND_Y)], fill=C["fence"])
        d.point((x, 93), fill=C["fence"])

    # A crooked bare tree on the left, branches running off the top.
    trunk = [rect(10, 40, 17, GROUND_Y + 1), rect(13, 20, 16, 44)]
    branches = []
    for (x0, y0, x1, y1, w) in ((15, 46, 34, 30, 3), (14, 34, 2, 18, 3), (16, 26, 26, 6, 2), (31, 32, 40, 26, 2),
                                (6, 22, 0, 12, 2)):
        branches.append(lambda dd, a=(x0, y0, x1, y1, w): dd.line([a[:2], a[2:4]], fill=255, width=a[4]))
    layer(img, trunk + branches, C["tree"], C["tree_line"])

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
