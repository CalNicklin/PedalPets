"""Forest backdrop and leaf sprites for the paper-doll pets.

Drawn procedurally with Pillow at screen size (160x128) in flat colour with
soft outlines (darker shades, not black, so the pet's ink lines stay on top).
The middle is kept open for the pet; feet stand at y = 124.

  draw() -> RGB backdrop     leaf_sprites() -> list of RGBA leaf images
"""
import random

from PIL import Image, ImageDraw

W, H = 160, 128
GROUND_Y = 113          # top of the ground strip
FEET_Y = 124            # where the pet's feet stand (canvas baseline)

C = {
    "sky":        (239, 230, 207),
    "glow":       (245, 218, 168),
    "hills":      (211, 220, 192),
    "hills2":     (196, 209, 176),
    "trunk":      (138, 106, 80),
    "trunk_line": (77, 58, 43),
    "leaf1":      (122, 162, 98),
    "leaf2":      (95, 138, 82),
    "leaf_line":  (63, 95, 58),
    "bush":       (111, 154, 91),
    "ground":     (203, 180, 138),
    "ground_dk":  (181, 156, 114),
    "ground_line": (143, 122, 87),
    "grass":      (127, 166, 94),
    "cap":        (200, 70, 58),
    "cap_line":   (122, 40, 34),
    "stem":       (240, 232, 214),
    "white":      (250, 248, 242),
}


def layer(img, shapes, fill, line=None):
    """Draw the union of `shapes` (callables taking a Draw) filled, with a
    1 px outline around the union's edge only."""
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    for s in shapes:
        s(d)
    px = mask.load()
    out = img.load()
    for y in range(H):
        for x in range(W):
            if not px[x, y]:
                continue
            edge = line and any(
                not (0 <= x + dx < W and 0 <= y + dy < H) or not px[x + dx, y + dy]
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            # Off-screen edges aren't outlined (shapes run off the frame).
            if edge and all(0 <= x + dx < W and 0 <= y + dy < H for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[x, y] = line
            else:
                out[x, y] = fill


def circle(cx, cy, r):
    return lambda d: d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)


def rect(x0, y0, x1, y1):
    return lambda d: d.rectangle([x0, y0, x1, y1], fill=255)


def draw(seed=7):
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), C["sky"])
    d = ImageDraw.Draw(img)

    # Hazy sun low behind the trees, then two rows of distant hills.
    layer(img, [circle(116, 40, 20)], C["glow"])
    layer(img, [circle(x, 112, r) for x, r in ((10, 30), (52, 24), (92, 28), (138, 26), (170, 30))], C["hills"])
    layer(img, [circle(x, 120, r) for x, r in ((-6, 22), (34, 18), (74, 20), (112, 16), (150, 22))], C["hills2"])

    # Trees framing the sides; canopies run off the top.
    layer(img, [rect(8, 20, 19, GROUND_Y + 2), rect(141, 26, 150, GROUND_Y + 2)], C["trunk"], C["trunk_line"])
    layer(img, [circle(2, 10, 22), circle(24, 4, 18), circle(10, 30, 14), circle(32, 22, 10),
                circle(158, 8, 22), circle(136, 2, 16), circle(150, 30, 13), circle(128, 20, 9)],
          C["leaf1"], C["leaf_line"])
    layer(img, [circle(-2, 24, 10), circle(18, 14, 8), circle(160, 22, 10), circle(140, 12, 7)],
          C["leaf2"], C["leaf_line"])

    # Bushes at the edges of the clearing.
    layer(img, [circle(4, 106, 14), circle(22, 110, 10), circle(-4, 96, 10),
                circle(156, 106, 13), circle(140, 110, 9), circle(166, 96, 10)], C["bush"], C["leaf_line"])

    # Ground strip with a soft edge, specks and grass tufts.
    layer(img, [rect(0, GROUND_Y, W - 1, H - 1)], C["ground"])
    d.line([(0, GROUND_Y), (W - 1, GROUND_Y)], fill=C["ground_line"])
    for _ in range(40):
        x, y = rnd.randrange(W), rnd.randrange(GROUND_Y + 2, H)
        d.point((x, y), fill=C["ground_dk"])
    for x in list(range(4, 40, 7)) + list(range(122, 160, 6)) + [52, 66, 97, 110]:
        y = GROUND_Y + rnd.randrange(0, 3)
        d.line([(x, y), (x - 1, y - 3)], fill=C["grass"])
        d.line([(x + 1, y), (x + 2, y - 3)], fill=C["grass"])

    # Two little mushrooms by the right bush.
    for mx, my, r in ((128, GROUND_Y + 1, 4), (135, GROUND_Y + 3, 3)):
        d.rectangle([mx - 1, my - 3, mx + 1, my], fill=C["stem"])
        d.pieslice([mx - r, my - 3 - r, mx + r, my - 3 + r], 180, 360, fill=C["cap"], outline=C["cap_line"])
        d.point((mx - 1, my - 5), fill=C["white"])
    return img


LEAF_COLOURS = [(217, 130, 43), (181, 82, 46), (226, 179, 60), (138, 168, 79)]
LEAF = [".#####.", "#######", ".#####."]   # a leaf lying flat
LEAF_EDGE = ["#######"]                    # tumbling, seen edge-on
ROTATIONS = 8


def leaf_sprites():
    """[colour][rotation][flat/edge] RGBA sprites, tumbling = alternate flat/edge."""
    out = []
    for col in LEAF_COLOURS:
        per_rot = []
        for k in range(ROTATIONS):
            pair = []
            for rows in (LEAF, LEAF_EDGE):
                w, h = len(rows[0]), len(rows)
                im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                for y, r in enumerate(rows):
                    for x, ch in enumerate(r):
                        if ch == "#":
                            im.putpixel((x, y), (*col, 255))
                im = im.rotate(k * 180 / ROTATIONS, resample=Image.NEAREST, expand=True)
                pair.append(im.crop(im.getbbox()))
            per_rot.append(pair)
        out.append(per_rot)
    return out


# --- the crowd: critters at the edges who come out for the music ------------------
# Each faces left (flipped on the device to watch the pet). "up" is the critter
# standing; "peek" shows its top `peek` rows (just ears and eyes); "cheer" adds
# raised arms (the "arms" pixels, in outline colour).
CROWD_COLOURS = {"o": (66, 56, 52), "g": (168, 158, 148), "P": (232, 150, 150), "k": (28, 24, 24),
                 "w": (242, 236, 224), "f": (112, 172, 82), "F": (74, 120, 56), "y": (236, 214, 120)}
CRITTERS = {
    "mouse": {"up": [".o....o.",
                     "oPo..oPo",
                     ".oooooo.",
                     "okgggggo",
                     "oggggggo",
                     ".owwwwo.",
                     "..o..o.."], "peek": 4, "arms": [(0, 1), (0, 2), (7, 0), (7, 1)]},
    "frog":  {"up": [".oo..oo.",
                     "okyookyo",
                     "offffffo",
                     "offffffo",
                     ".oFFFFo.",
                     "oo....oo"], "peek": 2, "arms": [(0, 0), (1, 0), (6, 0), (7, 0)]},
}
# (centre x, bottom y, kind): on the bush tops and by the mushrooms; the middle stays open.
CROWD = [(10, 97, "mouse"), (150, 97, "mouse"), (30, 114, "frog"), (118, 114, "frog")]


def crowd_sprites(critters=None, colours=None):
    """{kind: [peek, up, cheer]} RGBA sprites (this scene's critters by default)."""
    critters = critters or CRITTERS
    colours = colours or CROWD_COLOURS
    out = {}
    for kind, spec in critters.items():
        rows = spec["up"]
        w, h = len(rows[0]), len(rows)

        def paint(rows, extra=()):
            ex = 1 if extra else 0                  # a row above for raised arms
            im = Image.new("RGBA", (w, len(rows) + ex), (0, 0, 0, 0))
            for y, r in enumerate(rows):
                for x, ch in enumerate(r):
                    if ch != ".":
                        im.putpixel((x, y + ex), (*colours[ch], 255))
            for x, y in extra:
                im.putpixel((x, y), (*colours["o"], 255))
            return im
        out[kind] = [paint(rows[:spec["peek"]]), paint(rows), paint(rows, spec["arms"])]
    return out


if __name__ == "__main__":
    import sys
    draw().save(sys.argv[1] if len(sys.argv) > 1 else "forest.png")
