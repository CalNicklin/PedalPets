# Reactive Pet — Design

Date: 2026-10-08
Status: approved design, revised after review; sub-project 1 ready for
implementation planning

## Goal

Replace "three looping animations picked by RMS threshold" with a pet that
feels alive and reactive to playing — in the spirit of Mini-Maui (Moana) and
Ninja Ninja (Afro Samurai): a loud, theatrical companion who is always on the
player's side. It notices musical events, reacts with authored, snappy
acting (anticipation → action → hold → settle), and its mood builds over time.

Non-goals: procedural bob/sway/wobble transforms on sprites (tried, rejected).
"Alive" comes from pose changes, eyes and well-timed reactions only.

## Decisions

| Topic | Decision |
|---|---|
| Personality | Hype fan — loves everything you play |
| Art format | Key-pose library (whole-character poses) + separate eye overlay |
| Art style | Afro Samurai ink: black / white / red / one mid-grey, thick brush lines |
| Art source (now) | Blender, driven by Claude via headless Python scripts (+ Blender MCP for viewport checks / image-to-3D) |
| Art source (later) | Commissioned artist — same deliverable: PNG frames + pose manifest |
| Validation | Mock input (serial keys + scripted timelines) on device; native unit tests |

## Architecture

```
 LiveAudio (ADC → detectors)   MockInput (serial keys / scripted timeline)
            \                    /
             MusicEvent stream + Features  (~100 Hz)
                        │
                     Brain        pure C++: Mood + ReactionPicker
                        │
                   Performer      plays reaction steps; EyeController
                        │
                    Renderer      background + pose + eye overlay → TFT
```

- `Brain`, `Performer`, `EyeController` are hardware-free C++ under
  `src/core/`. Time is passed in (`now_ms`), randomness comes from an injected
  seeded RNG. They compile and run under PlatformIO's `native` env.
- Input producers and the renderer live under `src/platform/` and are the
  only code touching Arduino / TFT_eSPI.
- Reactions, poses and idles are **data**. Core logic receives them as an
  `ArtTables` struct (pointers + counts) and contains no hard-coded
  reactions. Firmware passes the tables generated from `art/manifest.toml`;
  tests pass small hand-written fixture tables.

## Generated code

`tools/build_art.py` (system Python ≥ 3.11 for `tomllib`, plus Pillow) reads
`art/manifest.toml` and emits two headers:

- `src/gen/pose_meta.h` — plain C++, no Arduino includes: pose ids, crop
  rects, eye anchors, reactions, idles. Included by core and tests.
- `src/gen/pose_pixels.h` — `PROGMEM` pixel data. Included only by
  `renderer_tft`.

Frames are **cropped to their bounding box**; each pose stores
`{w, h, x_off, y_off}` relative to the 96×112 canvas. The renderer positions
by offset. This keeps placeholder RGB565 frames ≈ 10 KB each and carries
over unchanged to the 2 bpp art.

`platformio.ini`:

```ini
[env:esp32dev]
; existing settings, plus:
board_build.partitions = huge_app.csv

[env:native]
platform = native
test_framework = unity
build_src_filter = +<core/>
```

## Interfaces

```cpp
enum class EventType : uint8_t {
  Pick,        // note onset; strength 0..1 (light vs hard)
  BigHit,      // loud attack after relative quiet
  Flurry,      // sustained high onset rate (re-sent while it continues)
  SustainStart, SustainEnd,
  SwellStart,  SwellPeak,
  Cut,         // sudden silence after loud playing
};
struct MusicEvent { EventType type; uint32_t t_ms; float strength; };
struct Features   { float level; float onsetRate; };  // level normalised 0..1, onsetRate in onsets/s
```

Long silence is not an event: the Mood model handles it from `Features`.
Events are processed in arrival order; several may arrive in one tick.

## Mood model

Moods: `Asleep → Curious → IntoIt → Hyped`.

Energy, updated every tick (`dt` seconds):

```
if (level > energy) energy += (level - energy) * k_attack;   // k_attack = 0.3 per 10 ms tick
energy *= exp(-dt / tau);                                    // tau = 8 s
energy  = clamp(energy + eventBoost, 0, 1);
```

Event boosts: `BigHit` +0.2, `Flurry` +0.1, `Pick` +0.03 × strength.

Transitions:

- Awake moods by energy with hysteresis (up / down):
  IntoIt 0.35 / 0.25, Hyped 0.70 / 0.55. These threshold-driven
  transitions require ≥ 2 s dwell in the current mood.
- `Curious → Asleep`: `level` below `noiseFloor` (0.03) for 10 s. The silence
  timer runs **only in Curious**, so a quiet pet steps Hyped → IntoIt →
  Curious → Asleep. Entering Asleep sets `energy = 0`.
- `Asleep → Curious`: any event, **immediately** (no dwell). The event is
  consumed by the mood model; it triggers no reaction of its own.

All constants (`k_attack`, `tau`, boosts, thresholds, dwell, `noiseFloor`,
silence timeout) live in one `MoodConfig` struct.

Mood transitions trigger reactions: entering `Curious` from `Asleep` →
**Wake**; entering `Asleep` → **DriftOff**. Other transitions only change the
idle loop. A mood change during a reaction takes effect when that reaction
ends.

## Idles

Each mood has an idle **cycle**: a short loop of poses played continuously,
with a rest period per pose (`[idles.<Mood>] poses, period`).

- Logic ticks every 10 ms and the screen renders every 3rd tick (30 ms), on a
  fixed grid. Every pose — idle or reaction step — is held a whole number of
  frames; uneven 1-frame/2-frame holds read as stutter.
- Playing harder speeds the cycle up: rate × (1 + 0.6 × energy), applied in
  whole-frame steps with 0.6-frame hysteresis so it never flickers between
  two speeds.
- A mood change waits for the current pose to finish; an idle (re)starts at
  pose 0 at the current speed.
- Picks don't step the idle directly (tried: irregular picks made it
  stutter); they raise energy, which raises the cycle speed.

(Revised 2026-10-30 after simulator measurements: the original "beat-step"
held 2–3 poses for 0.4–1 s and read as a slideshow.)

## Reactions

| Trigger | Reaction | Notes |
|---|---|---|
| BigHit | Blown back — "OHHH!" | |
| Flurry | Frantic headbang / air-guitar | a repeat Flurry extends it |
| SustainStart | Awe — hands on head, leaning in | holds until `SustainEnd` |
| SwellStart | Crouch lower and lower, then leap | crouch holds until `SwellPeak` |
| Cut | Freeze mid-move → point at you "YEAH!" | freeze uses `@current` |
| Wake | Startled jolt, look around | from Asleep → Curious |
| DriftOff | Big yawn | on entering Asleep |

### Steps

A reaction is a list of steps:

```
{ pose, hold, eyes, until, until_max }
```

- `pose`: a pose id, or `"@current"` = keep whatever pose is on screen.
- `hold`: ms, or `[min, max]` (picked uniformly at random each time it
  plays).
- `eyes`: an eye state, or omitted = `Auto`.
- `until` (optional): event name. The step lasts at least `hold`, then
  continues to wait until that event arrives or `until_max` elapses
  (default 5000 ms). Either way it then **continues to the next step** (so
  a Swell with no `SwellPeak` still leaps). If the `until` event already
  arrived since the reaction started, the step plays its `hold` only.

### Picking

- Each reaction has a `trigger` and an optional `moods` filter. The picker
  chooses among reactions matching the trigger and the current mood; none
  matching → nothing plays.
- Never repeat the last variant used for that trigger when another exists.
- Reactions fire in Curious, IntoIt, Hyped. Asleep only produces Wake (via
  the mood transition).
- **Cooldown:** 1.5 s per trigger type, measured from reaction start,
  overridable per reaction.

### Priority and interrupts

Order: **Wake** > BigHit > Cut > Flurry > Swell > Sustain > **DriftOff**.

- Wake cannot be interrupted.
- DriftOff is interrupted by any event (which wakes the pet → Wake).
- Otherwise a higher-priority trigger interrupts the current reaction once
  ≥ 120 ms have passed since that reaction started. Equal- or
  lower-priority triggers are dropped (not queued).
- **Extend rule:** a trigger equal to the one that started the current
  reaction restarts the current step's hold timer instead of being dropped
  (no cooldown applies). This keeps a continuing Flurry in one reaction
  rather than reaction → idle → reaction.
- When a reaction ends the Performer returns to the current mood's idle.

## Eyes

Eye states: `Open, Blink, LookL, LookR, Wide, HappyClosed`.

- Each pose declares an eye anchor `(x, y)` or `eyes = "baked"` (turned-away
  poses, all Asleep poses). No overlay is drawn for baked poses.
- `EyeController` in `Auto`: blink every 2–6 s (120 ms); glance L/R every
  4–10 s for 400–800 ms. Off while Asleep. A reaction step's explicit eye
  state overrides it.

## Art spec (applies to every art source)

- Canvas 96×112 per pose, consistent scale, feet on a fixed baseline
  (y = 108), character horizontally centred. Stored cropped (see Generated
  code). The manifest's `[canvas]` table can override this (the placeholder
  wizard uses the full 160×128 screen for its spell effects).
- Final palette exactly 4 colours: black, white, red, mid-grey. Stored at
  2 bpp. Eye overlay sprites use the same palette plus a transparent key.
- Background (off-white + optional red sun disc) is drawn by the renderer,
  not baked into frames.
- Deliverable: PNG per pose + entries in `art/manifest.toml`.

Starter pack ≈ 10 idle poses + ≈ 40 reaction poses + 6 eye states.

## Manifest format

```toml
[poses.hyped_idle_1]
src   = "art/poses/hyped_idle_1.png"   # or "<sheet.png>#<frame>" (placeholders)
eyes  = [44, 30]                        # anchor on the 96x112 canvas, or "baked"

[[reactions]]
id       = "big_hit_a"
trigger  = "BigHit"            # BigHit, Cut, Flurry, Swell, Sustain, Wake, DriftOff
moods    = ["IntoIt", "Hyped"] # optional
cooldown = 1500                # optional
steps = [
  { pose = "recoil_1", hold = 80,         eyes = "Wide" },
  { pose = "recoil_2", hold = [350, 500], eyes = "Wide" },
  { pose = "recoil_3", hold = 250 },
]

[idles]
Hyped = ["hyped_idle_1", "hyped_idle_2"]
```

## Sub-project 1 — Brain + Performer with mock input (implement now)

Scope:

1. Split `src/main.cpp` into `src/core/` (`music_event.h`, `art_tables.h`,
   `mood.*`, `brain.*`, `performer.*`, `eyes.*`, `rng.h`) and
   `src/platform/` (`mock_input.*`, `renderer_tft.*`, `main.cpp`).
2. `tools/build_art.py` as described in Generated code, replacing
   `tools/convert_sprites.py`. Validation in this sub-project: unknown pose
   references, missing files, out-of-range sheet frames, every pose has an
   eye anchor or `baked`, every mood has a non-empty idle. Palette, canvas,
   baseline checks and the contact sheet are **deferred to sub-project 2**
   (wizard frames would fail them).
3. Placeholder manifest mapping wizard sheet frames (Idle/Run/Attack1/
   Attack2: 8 frames, Death: 7, Take hit: 3, Jump/Fall: 2) to poses, e.g.
   Idle → Curious idle, Run → IntoIt idle, Attack1 → Hyped idle,
   Take hit → BigHit / Wake, Attack2 → Flurry, Jump/Fall → Swell / Sustain,
   Death → DriftOff / Asleep idle. One reaction per trigger is enough; the
   picker supports variants but the placeholder manifest need not supply
   them. Eye overlay drawn as simple placeholder primitives at each anchor.
4. Mock input over serial (115200), ignoring `\r` and `\n`:
   `p` pick (strength 0.4), `P` hard pick (strength 0.9), `h` BigHit,
   `f` Flurry (burst of picks + event), `s`/`S` sustain start/end,
   `w`/`W` swell start/peak, `c` Cut, `+`/`-` base level ±0.1,
   `0` silence, `1`–`3` run scripted timeline, `d` toggle debug HUD (mood,
   energy, reaction, step), `r` reset. Every pick also lifts `level` to at
   least its strength, decaying back to the base level over 300 ms, so
   repeated picking alone can reach IntoIt.
5. Scripted timelines as `{t_ms, action}` arrays; script 1 is a 60 s "set":
   silence → wake → noodling → build → flurry → big hit → cut → sustain →
   fade → asleep.
6. Remove the current threshold state machine. LiveAudio is not wired in
   this sub-project (the ADC sampling code is retained but unused until
   sub-project 3).

Tests (`pio test -e native`, Unity, fixture `ArtTables`):

- Mood: energy formula, hysteresis, dwell on threshold transitions only,
  immediate wake, silence timer only in Curious, energy reset on sleep,
  Wake / DriftOff on the right transitions.
- Picker: trigger + mood filter, no consecutive repeat of a variant,
  cooldown from reaction start, Asleep consumes events.
- Performer: step timing incl. `[min,max]` holds, `until` (early event,
  late event, `until_max` expiry continues), `@current`, interrupt only
  ≥ 120 ms after reaction start, Wake uninterruptible, DriftOff
  interruptible, lower-priority dropped, extend rule, idle resumes at
  pose 0, beat-step rules + timer fallback, no beat-step during reactions.
- Eyes: blink/glance scheduling with seeded RNG, off in Asleep, reaction
  override.

Acceptance: all native tests pass; firmware builds and fits the
`huge_app` partition; on device, script 1 plays end to end with reactions
visibly in sync with the HUD, and keyboard events produce reactions within
one frame (≤ 33 ms).

## Sub-project 2 — Art pipeline (own spec later)

Blender spike: concept image → image-to-3D → Rigify → 3–4 toon/ink-rendered
poses viewed on the TFT. Then full pack, 2 bpp storage, real eye set, and
the deferred validator checks + contact sheet. Open: which image-to-3D /
auto-rig route is fully hands-off (Mixamo has no API).

### Spike results (2026-10-30)

- `art/blender/pet.py` builds and animates a procedural Afro-Samurai-style
  hype character (afro, red headband with trailing tails, kimono) headlessly;
  `tools/build_pet.sh` renders → inks (`tools/ink.py`: palette snap + 1 px
  ink lines) → writes `art/pet/manifest.toml` → regenerates firmware headers.
- Motion: cubic splines through key poses; tails/afro follow-through derived
  from body motion; everything rendered on ones (30 ms per frame).
- Smooth transitions by construction: every loop and reaction starts/ends on
  a shared hub pose; idle loops hand over only at loop end; reactions have
  loop sections (extend / loop-until) and a **matched entry** table (start at
  the reaction frame most like what's on screen).
- Storage: 4-bit palette, index 0 transparent, over an off-white background
  with a sun disc. 366 frames ≈ 1 MB; firmware 43% of the 3 MB partition.
- Device: 33 pose changes/s, every frame on time, 0% judder.

## Sub-project 3 — Live signal detection (own spec later)

Detectors for Pick / BigHit / Flurry / Sustain / Swell / Cut and `Features`
from the ADC, behind the same event interface. Tuned natively against
recorded guitar WAVs with expected-event fixtures. Blocked on soldering the
1/4" input jack.

## Deferred ideas

- A single pending slot (~300 ms expiry) so a Cut straight after a BigHit
  still plays. Add only if dropped Cuts feel wrong in practice.
