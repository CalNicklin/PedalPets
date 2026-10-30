"""PedalPets hype character, built and animated procedurally in Blender.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P art/blender/pet.py -- <out_dir> [action ...]

Renders flat-colour RGBA frames (2x the 96x112 canvas) into <out_dir>/raw/<action>_NN.png
and writes <out_dir>/actions.json describing each action. tools/ink.py turns the
raw renders into palette ink frames and a manifest.
"""
import json
import math
import os
import sys

import bpy

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(ARGS[0] if ARGS else "art/pet")
ONLY = set(ARGS[1:])

CANVAS_W, CANVAS_H, BASELINE = 96, 112, 108
SS = 2                         # render supersampling factor
VIEW_H = 2.5                   # world units visible vertically

# Flat material colours; tools/ink.py maps them to the palette.
COLOURS = {
    "ink":   (0.02, 0.02, 0.02),   # kimono, afro, eyebrows
    "skin":  (0.45, 0.45, 0.45),   # face, hands
    "red":   (0.80, 0.05, 0.05),   # headband
    "white": (1.00, 1.00, 1.00),   # eyes, teeth
}


# --- scene -------------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "BLENDER_WORKBENCH"
    s.display.shading.light = "FLAT"
    s.display.shading.color_type = "MATERIAL"
    s.display.render_aa = "OFF"
    s.render.film_transparent = True
    s.render.resolution_x = CANVAS_W * SS
    s.render.resolution_y = CANVAS_H * SS
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    s.view_settings.view_transform = "Standard"

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = VIEW_H
    cam = bpy.data.objects.new("cam", cam_data)
    s.collection.objects.link(cam)
    # Feet (z=0) land on the canvas baseline.
    bottom_px = CANVAS_H - BASELINE
    z_centre = VIEW_H / 2 - bottom_px / CANVAS_H * VIEW_H
    cam.location = (0, -10, z_centre)
    cam.rotation_euler = (math.radians(90), 0, 0)
    s.camera = cam


MATS = {}


def material(name):
    if name not in MATS:
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*COLOURS[name], 1)
        MATS[name] = m
    return MATS[name]


def link(obj, parent, loc):
    bpy.context.scene.collection.objects.link(obj) if obj.name not in bpy.context.scene.collection.objects else None
    obj.parent = parent
    obj.location = loc
    return obj


def joint(name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = parent
    e.location = loc
    e.rotation_mode = "XYZ"
    return e


def blob(name, mat, parent, loc, scale, rot=(0, 0, 0), segs=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material(mat))
    bpy.ops.object.shade_smooth()
    o.parent = parent
    o.location = loc
    o.scale = scale
    o.rotation_euler = [math.radians(a) for a in rot]
    return o


def ring(name, mat, parent, loc, major, minor, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=48, minor_segments=12)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material(mat))
    o.parent = parent
    o.location = loc
    o.scale = scale
    o.rotation_euler = [math.radians(a) for a in rot]
    return o


# --- character ---------------------------------------------------------------

J = {}   # joints by name; animation drives only these


def build_character():
    turn = J["turn"] = joint("turn")                     # 3/4 view
    turn.rotation_euler = (0, 0, math.radians(-22))
    root = J["root"] = joint("root", turn)               # squash/stretch about the feet
    # Legs stay planted; the body bounces on top of them.
    for side in (-1, 1):
        blob(f"leg{side}", "ink", root, (0.17 * side, 0, 0.2), (0.12, 0.12, 0.24))
        blob(f"foot{side}", "ink", root, (0.2 * side, -0.07, 0.05), (0.15, 0.24, 0.07))

    hips = J["hips"] = joint("hips", root, (0, 0, 0.4))
    blob("torso", "ink", hips, (0, 0, 0.28), (0.36, 0.27, 0.38))     # kimono
    blob("sash", "red", hips, (0, 0, 0.1), (0.37, 0.28, 0.06))
    blob("collar", "skin", hips, (0, -0.2, 0.55), (0.13, 0.06, 0.12))  # open neckline

    chest = J["chest"] = joint("chest", hips, (0, 0, 0.5))
    for side, name in ((-1, "R"), (1, "L")):
        sh = J[f"shoulder{name}"] = joint(f"shoulder{name}", chest, (0.36 * side, 0, 0.06))
        sh.rotation_euler = (0, 0, 0)
        blob(f"arm{name}", "ink", sh, (0.04 * side, 0, -0.24), (0.1, 0.1, 0.24), rot=(0, 10 * side, 0))
        J[f"hand{name}"] = hand = joint(f"hand{name}", sh, (0.1 * side, 0, -0.44))
        blob(f"fist{name}", "skin", hand, (0, 0, 0), (0.1, 0.1, 0.1))

    neck = J["neck"] = joint("neck", chest, (0, 0, 0.1))
    head = J["head"] = joint("head", neck, (0, 0, 0.04))
    blob("face", "skin", head, (0, 0, 0.3), (0.32, 0.29, 0.34))
    afro = J["afro"] = joint("afro", head, (0, 0.2, 0.52))
    blob("afro", "ink", afro, (0, 0.05, 0.05), (0.6, 0.42, 0.46), segs=24)
    ring("band", "red", head, (0, 0.0, 0.42), 0.31, 0.045, scale=(1.03, 0.95, 1), rot=(-8, 0, 0))
    # Headband tails trail behind the head (secondary motion).
    for side, name in ((-1, "R"), (1, "L")):
        t1 = J[f"tail{name}1"] = joint(f"tail{name}1", head, (0.2 * side, 0.25, 0.42))
        blob(f"tail{name}a", "red", t1, (0.13 * side, 0.03, -0.05), (0.17, 0.03, 0.05), rot=(0, 20 * side, 0))
        t2 = J[f"tail{name}2"] = joint(f"tail{name}2", t1, (0.3 * side, 0.04, -0.1))
        blob(f"tail{name}b", "red", t2, (0.13 * side, 0.0, -0.04), (0.16, 0.025, 0.045), rot=(0, 25 * side, 0))
    # Face: brows (ink), eyes (white slits), mouth.
    face = J["face"] = joint("face", head, (0, -0.27, 0.3))
    for side, name in ((-1, "R"), (1, "L")):
        eye = J[f"eye{name}"] = joint(f"eye{name}", face, (0.11 * side, 0, 0.01))
        blob(f"eye{name}", "white", eye, (0, 0, 0), (0.075, 0.03, 0.04))
        brow = J[f"brow{name}"] = joint(f"brow{name}", face, (0.12 * side, -0.01, 0.08))
        blob(f"brow{name}", "ink", brow, (0, 0, 0), (0.1, 0.03, 0.025), rot=(0, 14 * side, 0))
    J["mouth"] = mouth = joint("mouth", face, (0, 0, -0.14))
    blob("mouth", "ink", mouth, (0, -0.01, 0), (0.09, 0.03, 0.025))


# --- poses & animation -------------------------------------------------------
#
# A pose is {joint: {"r": (x,y,z) degrees, "l": (dx,dy,dz), "s": (x,y,z)}},
# relative to the rest pose. Actions are key poses at frame numbers; frames in
# between come from a cubic (Catmull-Rom style) spline through the keys, so
# motion eases naturally. Loops use a cyclic spline. Headband tails and the
# afro are not keyed: they follow the body's motion with a lag (follow-through).

def P(**joints):
    return joints


def merge(*poses):
    out = {}
    for p in poses:
        for j, ch in p.items():
            out.setdefault(j, {}).update(ch)
    return out


def arms(r_y, l_y=None, r_x=0, l_x=None):
    """Raise arms in the screen plane (degrees outward-up); right arm is -x."""
    l_y = -r_y if l_y is None else l_y
    l_x = r_x if l_x is None else l_x
    return P(shoulderR={"r": (r_x, r_y, 0)}, shoulderL={"r": (l_x, l_y, 0)})


def eyes(sz, sx=1.0):
    return P(eyeR={"s": (sx, 1, sz)}, eyeL={"s": (sx, 1, sz)})


def brows(up):
    return P(browR={"l": (0, 0, up)}, browL={"l": (0, 0, up)})


def mouth(w, h):
    return P(mouth={"s": (w, 1, h)})


HUB = merge(arms(6), P(mouth={"s": (1.1, 1, 1)}))
ASLEEP = merge(
    P(hips={"l": (0, 0, -0.26), "r": (16, 0, 0)}, chest={"r": (14, 0, 0)},
      head={"r": (26, 0, 6)}, root={"s": (1.04, 1, 0.97)}),
    arms(4, r_x=-18), eyes(0.12), brows(-0.01), mouth(0.6, 1.4))


def stance(**kw):
    return merge(HUB, *kw.values())


ACTIONS = {}


def action(name, frames, keys, loop=False, **meta):
    ACTIONS[name] = {"frames": frames, "keys": keys, "loop": loop, **meta}


# Idle loops: start and end on HUB (Asleep on ASLEEP) so they hand over cleanly.
action("curious", 64, [
    (0, HUB),
    (16, merge(HUB, P(head={"r": (0, 6, 10)}, chest={"r": (0, 2, 0)}, root={"s": (1.012, 1, 0.985)},
                      browL={"l": (0, 0, 0.02)}))),
    (32, merge(HUB, P(head={"r": (-4, 0, 0)}, chest={"r": (-3, 0, 0)}, root={"s": (0.99, 1, 1.015)}))),
    (46, merge(HUB, P(head={"r": (0, -5, -10)}, browR={"l": (0, 0, 0.02)}))),
    (49, merge(HUB, P(head={"r": (0, -5, -10)}), eyes(0.1))),
    (52, merge(HUB, P(head={"r": (0, -4, -8)}))),
    (64, HUB),
], loop=True, idle="Curious")

action("groove", 24, [
    (0, HUB),
    (6, merge(HUB, P(head={"r": (18, 0, 0)}, chest={"r": (6, 0, 0)}, hips={"l": (0, 0, -0.05)},
                     root={"s": (1.04, 1, 0.95)}), arms(6, r_x=16, l_x=-16), mouth(1.2, 1.6))),
    (12, merge(HUB, P(head={"r": (-6, 0, 0)}, hips={"l": (0, 0, 0.02)}, root={"s": (0.98, 1, 1.02)}))),
    (18, merge(HUB, P(head={"r": (4, 0, 0)}), arms(6, r_x=-10, l_x=10))),
    (24, HUB),
], loop=True, idle="IntoIt")

action("hyped", 16, [
    (0, HUB),
    (4, merge(HUB, P(head={"r": (30, 0, 0)}, chest={"r": (10, 0, 0)}, hips={"l": (0, 0, -0.08)},
                     root={"s": (1.07, 1, 0.9)}), arms(100, -20), mouth(1.3, 3), brows(-0.015))),
    (8, merge(HUB, P(head={"r": (-12, 0, 0)}, chest={"r": (-4, 0, 0)}, hips={"l": (0, 0, 0.06)},
                     root={"s": (0.95, 1, 1.07)}), arms(150, -30), mouth(1.4, 3.5))),
    (12, merge(HUB, P(head={"r": (6, 0, 0)}), arms(60, -15), mouth(1.2, 1.8))),
    (16, HUB),
], loop=True, idle="Hyped")

action("asleep", 48, [
    (0, ASLEEP),
    (24, merge(ASLEEP, P(root={"s": (1.02, 1, 1.0)}, head={"r": (30, 0, 6)}), mouth(0.7, 2.2))),
    (48, ASLEEP),
], loop=True, idle="Asleep")

# Reactions: start and end on HUB.
BLOWN = merge(P(hips={"r": (-18, 0, 0), "l": (0, 0, 0.06)}, chest={"r": (-10, 0, 0)},
                head={"r": (-22, 0, 0)}, root={"s": (0.94, 1, 1.08)}),
              arms(130), mouth(1.6, 4.5), eyes(1.8, 1.2), brows(0.05))
action("big_hit", 31, [
    (0, HUB),
    (3, merge(HUB, P(root={"s": (1.04, 1, 0.95)}, head={"r": (8, 0, 0)}), eyes(0.6))),
    (7, BLOWN),
    (16, merge(BLOWN, P(head={"r": (-17, 0, 0)}), arms(120))),
    (23, merge(HUB, P(hips={"r": (6, 0, 0)}, head={"r": (8, 0, 0)}, root={"s": (1.02, 1, 0.97)}))),
    (30, HUB),
], trigger="BigHit", entry_window=4)

BANG_UP = merge(HUB, P(head={"r": (-10, 0, 0)}), arms(40, -70, r_x=10), mouth(1.2, 2))
BANG_DOWN = merge(HUB, P(head={"r": (38, 0, 0)}, chest={"r": (14, 0, 0)}, hips={"l": (0, 0, -0.06)},
                         root={"s": (1.06, 1, 0.9)}), arms(55, -60, r_x=-10), mouth(1.4, 3.5), brows(-0.02))
action("flurry", 22, [
    (0, HUB), (3, BANG_UP), (6, BANG_DOWN), (9, BANG_UP), (12, BANG_DOWN), (15, BANG_UP), (21, HUB),
], trigger="Flurry", loop_from=3, loop_len=12, entry_window=9)

AWE = merge(HUB, P(hips={"r": (8, 0, 0)}, head={"r": (-8, 0, 0)}), arms(150, r_x=-15),
            eyes(1.7, 1.15), mouth(1.0, 3.2), brows(0.045))
action("sustain", 39, [
    (0, HUB),
    (10, AWE),
    (18, merge(AWE, P(head={"r": (-8, 6, 4)}, root={"s": (1.0, 1, 1.02)}))),
    (26, AWE),
    (38, HUB),
], trigger="Sustain", loop_from=10, loop_len=16, loop_until="SustainEnd", loop_max=6000,
   entry_window=6)

CROUCH = merge(HUB, P(hips={"l": (0, 0, -0.18), "r": (10, 0, 0)}, root={"s": (1.08, 1, 0.86)},
                      head={"r": (-6, 0, 0)}), arms(30, r_x=30), eyes(0.7), brows(-0.03), mouth(0.8, 1))
action("swell", 39, [
    (0, HUB),
    (12, CROUCH),
    (16, merge(CROUCH, P(root={"s": (1.09, 1, 0.84)}, hips={"l": (0, 0, -0.19), "r": (10, 0, 0)}))),
    (20, CROUCH),
    (24, merge(HUB, P(hips={"l": (0, 0, 0.32)}, root={"s": (0.9, 1, 1.12)}, head={"r": (-10, 0, 0)}),
               arms(160), eyes(1.6), mouth(1.5, 4))),
    (28, merge(HUB, P(hips={"l": (0, 0, 0.36)}), arms(150), eyes(1.4), mouth(1.4, 3))),
    (32, merge(HUB, P(hips={"l": (0, 0, -0.1)}, root={"s": (1.1, 1, 0.88)}), arms(40))),
    (38, HUB),
], trigger="Swell", loop_from=12, loop_len=8, loop_until="SwellPeak", loop_max=5000,
   entry_window=6)

POINT = merge(HUB, P(chest={"r": (0, 0, -8)}, head={"r": (-4, 0, -6)}), arms(75, r_x=-35),
              mouth(1.5, 1.6), brows(0.02))
action("cut", 21, [
    (0, HUB), (4, POINT), (14, merge(POINT, P(head={"r": (-2, 0, -4)}))), (20, HUB),
], trigger="Cut", freeze_ms=450)

action("wake", 29, [
    (0, ASLEEP),
    (3, merge(HUB, P(hips={"l": (0, 0, 0.15)}, root={"s": (0.9, 1, 1.12)}), arms(60), eyes(1.8, 1.2),
              brows(0.05), mouth(1.2, 3))),
    (8, merge(HUB, eyes(1.5, 1.1), brows(0.03))),
    (13, merge(HUB, P(head={"r": (0, 0, 25)}), eyes(1.2))),
    (20, merge(HUB, P(head={"r": (0, 0, -25)}), eyes(1.2))),
    (28, HUB),
], trigger="Wake", start=ASLEEP)

action("drift_off", 33, [
    (0, HUB),
    (10, merge(HUB, P(root={"s": (0.96, 1, 1.06)}, head={"r": (-12, 0, 0)}), arms(160), eyes(0.1),
               mouth(1.3, 5))),
    (18, merge(HUB, P(head={"r": (8, 0, 0)}), arms(10), eyes(0.4), mouth(0.8, 1.4))),
    (32, ASLEEP),
], trigger="DriftOff", entry_window=6)


# --- interpolation -----------------------------------------------------------

CHANNELS = (("r", (0, 0, 0)), ("l", (0, 0, 0)), ("s", (1, 1, 1)))


def channel(pose, j, ch, default):
    return pose.get(j, {}).get(ch, default)


def spline(keys, f, n, loop):
    """Cubic Hermite through (t, value) keys with finite-difference tangents."""
    ts = [k[0] for k in keys]
    vs = [k[1] for k in keys]
    if loop:  # last key equals first; wrap neighbours
        ext_t = [ts[-2] - n] + ts + [ts[1] + n]
        ext_v = [vs[-2]] + vs + [vs[1]]
    else:     # flat ends: hold first/last
        ext_t = [ts[0] - 1] + ts + [ts[-1] + 1]
        ext_v = [vs[0]] + vs + [vs[-1]]
    if loop:
        f = f % n
    f = min(max(f, ts[0]), ts[-1])
    i = max(k for k in range(len(ts) - 1) if ts[k] <= f) if f < ts[-1] else len(ts) - 2
    a, b = i + 1, i + 2                       # indices into ext arrays
    t0, t1 = ext_t[a], ext_t[b]
    p0, p1 = ext_v[a], ext_v[b]
    m0 = (ext_v[b] - ext_v[a - 1]) / (ext_t[b] - ext_t[a - 1]) * (t1 - t0)
    m1 = (ext_v[b + 1] - ext_v[a]) / (ext_t[b + 1] - ext_t[a]) * (t1 - t0)
    if not loop and (a == 1):
        m0 = 0.0
    if not loop and (b == len(ext_t) - 2):
        m1 = 0.0
    u = (f - t0) / (t1 - t0) if t1 > t0 else 0.0
    h00, h10 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u
    h01, h11 = -2 * u**3 + 3 * u**2, u**3 - u**2
    return h00 * p0 + h10 * m0 + h01 * p1 + h11 * m1


KEYED = ("root", "hips", "chest", "shoulderR", "shoulderL", "neck", "head", "eyeR", "eyeL",
         "browR", "browL", "mouth")


def evaluate(act, f):
    keys, n, loop = act["keys"], act["frames"], act["loop"]
    pose = {}
    for j in KEYED:
        pose[j] = {}
        for ch, default in CHANNELS:
            pose[j][ch] = tuple(spline([(t, channel(p, j, ch, default)[i]) for t, p in keys], f, n, loop)
                                for i in range(3))
    # Keep eyes from inverting where the spline overshoots a blink.
    for e in ("eyeR", "eyeL"):
        sx, sy, sz = pose[e]["s"]
        pose[e]["s"] = (sx, sy, max(0.08, sz))
    return pose


def bounce(pose):
    """Vertical position of the head, roughly (body height + squash)."""
    return pose["hips"]["l"][2] + 1.3 * (pose["root"]["s"][2] - 1) - 0.004 * pose["head"]["r"][0]


def secondary(act, f):
    """Tails and afro follow the head's vertical motion with a lag."""
    def vel(t, lag):
        return (bounce(evaluate(act, t - lag)) - bounce(evaluate(act, t - lag - 1))) * 30

    v1, v2 = vel(f, 2), vel(f, 4)
    droop = -18
    a1 = max(-60, min(50, droop - 260 * v1))
    a2 = max(-50, min(50, -8 - 300 * v2))
    afro = max(-0.1, min(0.1, -1.5 * vel(f, 1)))
    return {
        "tailR1": {"r": (0, a1, 0)}, "tailL1": {"r": (0, -a1, 0)},
        "tailR2": {"r": (0, a2, 0)}, "tailL2": {"r": (0, -a2, 0)},
        "afro": {"s": (1 + afro, 1, 1 - afro)},
    }


def apply(pose):
    """pose: {joint: {"r": (x,y,z) deg, "l": (dx,dy,dz), "s": (x,y,z)}} relative to rest."""
    for name, j in J.items():
        if name == "turn":
            continue
        rest = REST[name]
        p = pose.get(name, {})
        r = p.get("r", (0, 0, 0))
        l = p.get("l", (0, 0, 0))
        s = p.get("s", (1, 1, 1))
        j.rotation_euler = [REST_ROT[name][i] + math.radians(r[i]) for i in range(3)]
        j.location = [rest[i] + l[i] for i in range(3)]
        j.scale = s


REST = {}
REST_ROT = {}


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    reset_scene()
    build_character()
    for n, j in J.items():
        REST[n] = tuple(j.location)
        REST_ROT[n] = tuple(j.rotation_euler)
    raw = os.path.join(OUT, "raw")
    os.makedirs(raw, exist_ok=True)
    meta = {}
    for name, act in ACTIONS.items():
        if ONLY and name not in ONLY:
            continue
        n = act["frames"]
        count = n if act["loop"] else n  # one-shots: frames 0..n-1 (last key at n-1)
        for f in range(count):
            apply(merge(evaluate(act, f), secondary(act, f)))
            render(os.path.join(raw, f"{name}_{f:02d}.png"))
        meta[name] = {k: v for k, v in act.items() if k not in ("keys", "start")}
        meta[name]["count"] = count
        print(f"rendered {name}: {count} frames")
    with open(os.path.join(OUT, "actions.json"), "w") as fp:
        json.dump(meta, fp, indent=1)


main()
