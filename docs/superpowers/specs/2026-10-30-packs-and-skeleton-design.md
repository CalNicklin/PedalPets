# Character & Scene Packs, and the Skeleton — Design

Date: 2026-10-30
Status: approved direction ("uncouple the mechanics from the character…
let's do a skeleton… build a believable skeleton")

## Why

Everything the pet *can do* — moods, the Mind, the choreographer's layering,
leaves that react, the panel-tuned timing — should survive swapping the art.
Today the jay is baked in: generated tables live in one fixed namespace, the
loop and renderer name jay channels (`CH_FLAPL`, `P_HEAD`), and the forest is
hard-wired into the renderer. A second character proves the split, and one
with arms can do much more with its world.

## Packs

- **Character pack** = rig (parts, axes, anchors, pixels, palette) + moves
  (vocabularies per mood and intent, reactions, marks) + roles: which channel
  hops, travels, faces, gusts (blows leaves), which part is the head, which
  channels the gaze steers. Generated into `src/gen/chars/<name>/`, namespace
  `<name>_gen`, exposing one `Character` struct.
- **Scene pack** = backdrop, ground line, leaf sprites and palette.
  `src/gen/scenes/<name>/`, one `Scene` struct.
- `src/gen/packs.h` (generated) lists every character and scene. The board
  switches live (`n` next character, `b` next scene); the simulator picks with
  `PEDALPETS_CHAR` / `PEDALPETS_SCENE`.
- Pixel data is plain `const` (flash on the ESP32), so the simulator compiles
  the same packs.
- Engine changes: channel masks widen to 32 bits (up to 24 channels);
  `DollPet` and the renderer take a `Character` and `Scene` at run time.
- Regression: the jay's simulator output is byte-identical before and after.

## Effectors

The world reacts to *effectors*, not "feet": each character names the parts
whose tips touch the world (jay: feet; skeleton: feet and hands). Hands near
the ground sweep leaves; wing/arm swings gust them.

## The skeleton

A cute-spooky little skeleton (big skull, small body), 3/4 view, ink style.

- Parts: legs (bend, stride), body (pelvis, spine, ribcage; lean, shape),
  skull (pitch, look, eyes as glowing pupils in the sockets), jaw (clacks),
  and for each arm an upper arm (shoulder angle) and a forearm with the hand
  baked in (elbow angle × hand shape: open, fist, point).
- Moves use the same moods, intents and reactions as the jay, with his own
  vocabulary: walks rather than hops; nods, headbangs with jaw clacks, air
  guitar, fist pumps, shimmies; scratches his skull, taps a foot, waves and
  beckons at you, shades his eyes to watch a leaf, sweeps and kicks leaves;
  his skull pops up when startled.
- Verified like the jay: strips, motion checks, panel ghosting, the story.

## Added after the first cut

- **Lift**: any part can be lifted by a channel (children follow): the
  skeleton's skull pops off when startled.
- **Tips and hands**: parts can mark a tip (a hand). Hands sweep leaves; a
  hand *closing* next to a leaf picks it up, holds it while it grips, and
  throws it with the hand's speed when it opens.
- **Approach and reach**: a character names the moves the Mind uses to walk
  up to a landed leaf and reach for it, and how far ahead the reach gets; the
  Mind investigates, approaches step by step, reaches once, then looks at
  what's in its hand.
- **Lying down**: past a 24° lean back, the body (and skull, jaw) roll back
  across the picture plane rather than into the scene, so the skeleton sits,
  lies back with his hands behind his head, and sleeps flat on his back.
- **Solo moves**: postures (lying back, sitting, picking up) play alone.
- **Graveyard** scene at dusk; demo script 4 ("quiet life") for the
  in-between behaviour.

## Not now

A crowd, memory of the player across sessions, an LLM director.
