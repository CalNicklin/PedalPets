# Paper-Doll Pet — Design

Date: 2026-10-30
Status: approved direction ("go with the paper doll, start with the jay")
Builds on: `2026-10-08-reactive-pet-design.md`

## Why

Whole-body clips make the pet feel *sectioned*: every mood is a loop, every
reaction starts and ends on a neutral hub pose, and the joins show. The goal
is a body with a range of movements that can be coordinated in any way — a
handful of moods, each with many variations, combining naturally and
unpredictably — and, later, driven by the *character* of the sound (groove vs
erratic palm-muted chugs vs ringing chords), not just its events.

## Idea

Render each body part separately in Blender, as a small library of authored
poses with 2D attachment points. On the device, stack the parts every frame
(back to front), each choosing its own pose. A **choreographer** decides what
each part does, layering authored **moves** (nod, flap, hop, look, startle…)
with smooth fade in/out, so motions overlap and blend instead of cutting
between clips.

Everything drawn is still an authored Blender render; the device only picks
and positions them (no runtime warping/wobble of sprites).

## Parts (jay)

Back to front: far wing, tail, legs, body, crest, head (eyes + upper beak
baked in), jaw, near wing.

| Part | Parent (anchor) | Pose axes (world-space where noted) |
|---|---|---|
| legs | ground | bend: stand / crouch / tuck |
| body | legs (hip) | lean (−24..24°), shape: stretch / normal / squash / big squash / fluff |
| head | body (neck) | pitch (world, −36..36°), look (−30..30°), eyes: open / wide / half / closed |
| crest | head | angle (world) |
| jaw | head | angle (world = head pitch + open) |
| tail | body | angle (world = body lean + tail) |
| wings (near, far) | body (shoulders) | flap (0..165°) × body lean bin |

- Parts render about their own pivot, with every other joint at rest, at
  world-space angles; so a child's world angle = parent's + its own, and the
  device picks the nearest image.
- Anchors: for each parent image, the canvas position of each child's pivot
  (¼-pixel fixed point). A child is drawn at
  `crop offset + (parent's anchor now − child's pivot at rest)`.
- A hop is a vertical offset applied at the ground; legs tuck while airborne.

## Runtime

- `DollPose`: hop, legs bend, body lean + shape, head pitch/look/eyes, jaw,
  crest, tail, wing near/far — continuous values.
- `Compositor` (hardware-free): DollPose → per part (image index, draw x, y).
- `Renderer`: background, then each part's 4-bit palette image with
  transparency.
- `Choreographer` (phase B): base stance per mood (eased, so mood changes
  glide), plus layered moves with weight envelopes; vocabulary and variation
  per mood; reactions are moves too.
- Telemetry/simulator log per-part image indices and positions, so the
  timeline tools redraw exactly what the board shows.

## Phases

- **A — parts and compositing:** Blender part libraries + anchors, build
  tooling, compositor + renderer, simulator/telemetry support; validated with
  scripted parameter sweeps.
- **B — choreographer:** moves, layering, mood stances and variations,
  reactions; driven by the existing Brain events/mood (mock input).
- **C — listening (later):** FFT features and drives (excitement, tension,
  groove-lock, surprise), tuned on real guitar recordings via the input jack.

## Risks

- Seams where parts meet: ink outlines and draw order must hide them;
  checked visually per part pair.
- Nearest-image quantisation: angle steps must be small enough that motion
  doesn't step visibly (6° steps; check at 30 fps).
- Lean coupling for wings is binned (3 bins); revisit if folded wings look
  detached on a leaning body.
