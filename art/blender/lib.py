"""Shared Blender machinery for PedalPets characters.

A character script (e.g. art/blender/jay.py) sets COLOURS, builds its joints
with the helpers here, declares KEYED joints and ACTIONS, then calls run().
Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P art/blender/<char>.py -- <out_dir> [action ...]

Renders flat-colour RGBA frames (2x the 96x112 canvas) into <out_dir>/raw/<action>_NN.png
and writes <out_dir>/actions.json (actions + palette) for tools/ink.py and
tools/pet_manifest.py.

Poses are {joint: {"r": (x,y,z) degrees, "l": (dx,dy,dz), "s": (x,y,z)}}
relative to rest. Frames between key poses come from a cubic spline (cyclic
for loops), so motion eases naturally.
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

COLOURS = {}                   # name -> ((linear r, g, b), "#output hex"); set by the character
KEYED = ()                     # joints driven by key poses; set by the character
STATIC = set()                 # joints never touched by apply() (e.g. the view turn)
J = {}                         # joints by name


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
        m.diffuse_color = (*COLOURS[name][0], 1)
        MATS[name] = m
    return MATS[name]


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


def cone(name, mat, parent, loc, r1, r2, depth, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=r1, radius2=r2, depth=depth)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material(mat))
    bpy.ops.object.shade_smooth()
    o.parent = parent
    o.location = loc
    o.scale = scale
    o.rotation_euler = [math.radians(a) for a in rot]
    return o


# --- poses & animation -------------------------------------------------------

def P(**joints):
    return joints


def merge(*poses):
    out = {}
    for p in poses:
        for j, ch in p.items():
            out.setdefault(j, {}).update(ch)
    return out


ACTIONS = {}


def action(name, frames, keys, loop=False, **meta):
    ACTIONS[name] = {"frames": frames, "keys": keys, "loop": loop, **meta}


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


def evaluate(act, f):
    keys, n, loop = act["keys"], act["frames"], act["loop"]
    pose = {}
    for j in KEYED:
        pose[j] = {}
        for ch, default in CHANNELS:
            pose[j][ch] = tuple(spline([(t, channel(p, j, ch, default)[i]) for t, p in keys], f, n, loop)
                                for i in range(3))
    # Keep scaled parts (blinks, beaks) from inverting where the spline overshoots.
    for j in KEYED:
        pose[j]["s"] = tuple(max(0.05, v) for v in pose[j]["s"])
    return pose


def apply(pose):
    """pose: {joint: {"r": (x,y,z) deg, "l": (dx,dy,dz), "s": (x,y,z)}} relative to rest."""
    for name, j in J.items():
        if name in STATIC:
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


def srgb(c):
    v = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return round(255 * max(0.0, min(1.0, v)))


def run(build, secondary, turn_deg=-22):
    """Build the character, render every action (or the ones named on the
    command line) and write actions.json. secondary(act, f) returns extra pose
    channels (follow-through) for frame f."""
    reset_scene()
    turn = J["turn"] = joint("turn")     # 3/4 view; characters parent their root to it
    turn.rotation_euler = (0, 0, math.radians(turn_deg))
    STATIC.add("turn")
    build()
    for n, j in J.items():
        REST[n] = tuple(j.location)
        REST_ROT[n] = tuple(j.rotation_euler)
    raw = os.path.join(OUT, "raw")
    os.makedirs(raw, exist_ok=True)
    meta = {}
    for name, act in ACTIONS.items():
        if ONLY and name not in ONLY:
            continue
        count = act["frames"]   # loops: key at `frames` equals frame 0; one-shots: last key at frames-1
        for f in range(count):
            apply(merge(evaluate(act, f), secondary(act, f)))
            render(os.path.join(raw, f"{name}_{f:02d}.png"))
        meta[name] = {k: v for k, v in act.items() if k != "keys"}
        meta[name]["count"] = count
        print(f"rendered {name}: {count} frames")
    palette = [{"name": n, "render": [srgb(c) for c in rgb], "out": out} for n, (rgb, out) in COLOURS.items()]
    with open(os.path.join(OUT, "actions.json"), "w") as fp:
        json.dump({"palette": palette, "actions": meta}, fp, indent=1)
