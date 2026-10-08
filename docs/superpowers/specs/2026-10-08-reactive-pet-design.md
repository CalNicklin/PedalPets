# Reactive Pet — Design

Date: 2026-10-08
Status: approved design; sub-project 1 ready for implementation planning

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
- Reactions and poses are **data**, generated from `art/manifest.toml` by
  `tools/build_art.py` into `src/gen/pose_table.h`. No reaction is hard-coded.

## Interfaces

```cpp
enum class EventType : uint8_t {
  Pick,        // note onset; strength 0..1 (light vs hard)
  BigHit,      // loud attack after relative quiet
  Flurry,      // sustained high onset rate
  SustainStart, SustainEnd,
  SwellStart,  SwellPeak,
  Cut,         // sudden silence after loud playing
};
struct MusicEvent { EventType type; uint32_t t_ms; float strength; };
struct Features   { float level; float onsetRate; };  // level normalised 0..1, onsetRate in onsets/s
```

Long silence is not an event: the Mood model handles it from `Features`.

## Mood model

Moods: `Asleep → Curious → IntoIt → Hyped`.

- `energy` ∈ [0,1]: rises with `level` (fast attack), decays slowly
  (release τ ≈ 8 s). `BigHit` adds +0.2, `Flurry` adds +0.1, `Pick` adds
  +0.02 × strength.
- Thresholds with hysteresis (up / down): IntoIt 0.35 / 0.25,
  Hyped 0.70 / 0.55. Minimum dwell 2 s in a mood before moving.
- `Asleep` after 10 s with `level` below the noise floor. Any event while
  Asleep → `Curious`.
- All constants live in one `MoodConfig` struct for tuning.

Mood transitions trigger reactions: entering `Curious` from `Asleep` → **Wake**;
entering `Asleep` → **Drift off**. Other transitions just switch idle loops.

## Idles

Each mood has an idle loop of 2–3 poses.

- Asleep / Curious: advance on a timer (≈ 600–900 ms per pose, jittered).
- IntoIt / Hyped: **beat-step** — each `Pick` advances the idle one pose
  (min 150 ms between steps); falls back to the timer if no pick for 1.5 s.
  This makes the nod follow the player's rhythm.

## Reactions

| Trigger | Reaction | Notes |
|---|---|---|
| BigHit | Blown back — "OHHH!" | |
| Flurry | Frantic headbang / air-guitar | |
| SustainStart | Awe — hands on head, leaning in | last step holds until `SustainEnd` (max 6 s) |
| SwellStart | Crouch lower and lower | last step holds until `SwellPeak` (max 5 s), then leap step |
| Cut | Freeze mid-move → point at you "YEAH!" | |
| → Curious from Asleep | Wake — startled jolt, look around | |
| → Asleep | Drift off — big yawn | |

- Each reaction has ~2 variants; the picker never repeats the last variant
  used for that trigger.
- A reaction is a list of steps: `{ pose, hold_ms, eyes, hold_until }` where
  `eyes` is a fixed eye state or `Auto`, and `hold_until` optionally names an
  event that ends the step early / extends it up to the hold cap.
- Reactions fire in moods Curious, IntoIt, Hyped. In Asleep, any event
  produces Wake instead.
- **Priority:** BigHit > Cut > Flurry > Swell > Sustain. A higher-priority
  trigger interrupts the current reaction once its first step has shown for
  ≥ 120 ms. Equal/lower-priority triggers are dropped (not queued).
- **Cooldown:** 1.5 s per trigger type by default, overridable per reaction.
- When a reaction ends the Performer returns to the current mood's idle.

## Eyes

Eye states: `Open, Blink, LookL, LookR, Wide, HappyClosed`.

- Each pose declares an eye anchor `(x, y)` or `eyes = "baked"`
  (e.g. turned-away poses) in which case no overlay is drawn.
- `EyeController` in `Auto`: blink every 2–6 s (120 ms), occasional glance
  L/R in every mood except Asleep (every 4–10 s, 400–800 ms). A reaction step's
  explicit eye state overrides it.

## Art spec (applies to every art source)

- Canvas 96×112 per pose, consistent scale, feet on a fixed baseline
  (y = 108), character horizontally centred.
- Final palette exactly 4 colours: black, white, red, mid-grey. Stored at
  2 bpp (≈ 2.7 KB/frame). Eye overlay sprites use the same palette plus a
  transparent key.
- Background (off-white + optional red sun disc) is drawn by the renderer,
  not baked into frames.
- Deliverable: PNG per pose + entries in `art/manifest.toml`.

Starter pack ≈ 10 idle poses + ≈ 40 reaction poses + 6 eye states.

## Manifest format

```toml
[poses.hyped_idle_1]
src   = "art/poses/hyped_idle_1.png"
eyes  = [44, 30]          # anchor, or "baked"

[[reactions]]
id       = "big_hit_a"
trigger  = "BigHit"       # EventType name, or "Wake" / "DriftOff"
cooldown = 1500           # optional
steps = [
  { pose = "recoil_1", hold = 80,  eyes = "Wide" },
  { pose = "recoil_2", hold = 400, eyes = "Wide" },
  { pose = "recoil_3", hold = 250 },              # eyes default Auto
]

[idles]
Hyped = ["hyped_idle_1", "hyped_idle_2"]
```

`tools/build_art.py` validates and fails the build on: unknown pose
references, missing files, wrong canvas size, more than 4 colours after
quantisation, content below the baseline, missing eye anchor. It also writes
`art/contact_sheet.png` for review.

## Sub-project 1 — Brain + Performer with mock input (implement now)

Scope:
1. Split `src/main.cpp` into `src/core/` (`music_event.h`, `mood.*`,
   `brain.*`, `performer.*`, `eyes.*`, `rng.h`) and `src/platform/`
   (`mock_input.*`, `renderer_tft.*`, `main.cpp`).
2. `tools/build_art.py` reading `art/manifest.toml` (Python `tomllib`),
   emitting `src/gen/pose_table.h`. For sub-project 1 it also accepts
   `src = "<sheet.png>#<frame>"` to slice the Evil Wizard sheets and emit
   RGB565 placeholder frames; 2 bpp output arrives with sub-project 2.
   Replaces `tools/convert_sprites.py`.
3. Placeholder manifest mapping wizard frames to the poses/reactions above
   (e.g. Idle → Curious idle, Run → IntoIt idle, Attack1 → Hyped idle,
   Take hit → BigHit / Wake, Attack2 → Flurry, Jump → Swell / Sustain,
   Death → Drift off / Asleep idle). Eye overlay is drawn as simple
   placeholder primitives at each anchor to exercise the mechanism.
4. Mock input over serial (115200):
   `p` pick, `P` hard pick, `h` BigHit, `f` Flurry (burst of picks + event),
   `s`/`S` sustain start/end, `w`/`W` swell start/peak, `c` Cut,
   `+`/`-` level up/down, `0` silence, `1`–`3` run scripted timeline,
   `d` toggle debug HUD (mood, energy, current reaction/step), `r` reset.
5. Scripted timelines as `{t_ms, action}` arrays; script 1 is a 60 s "set":
   silence → wake → noodling → build → flurry → big hit → cut → sustain →
   fade → asleep.
6. Remove the current threshold state machine; LiveAudio is not wired in
   this sub-project (the ADC sampling code is retained but unused until
   sub-project 3).

Tests (`pio test -e native`, Unity framework):
- Mood: energy rise/decay, hysteresis, min dwell, Asleep after 10 s silence,
  Wake / DriftOff triggered on the right transitions.
- Picker: correct reaction per trigger, no consecutive repeat of a variant,
  cooldown respected, Asleep → Wake.
- Performer: step timing, `hold_until` ends early on the named event and
  caps at max, priority interrupt only after 120 ms of first step,
  lower-priority dropped, return to idle, beat-step idle advance + timer
  fallback.
- Eyes: blink/glance scheduling with seeded RNG; reaction override.

Acceptance: all native tests pass; on device, script 1 plays end to end
with reactions visibly in sync with the HUD, and keyboard events produce
reactions within one frame (≤ 33 ms).

## Sub-project 2 — Art pipeline (own spec later)

Blender spike: concept image → image-to-3D → Rigify → 3–4 toon/ink-rendered
poses viewed on the TFT. Then full pack + 2 bpp storage + real eye set.
Open: which image-to-3D / auto-rig route is fully hands-off (Mixamo has no
API).

## Sub-project 3 — Live signal detection (own spec later)

Detectors for Pick / BigHit / Flurry / Sustain / Swell / Cut and `Features`
from the ADC, behind the same event interface. Tuned natively against
recorded guitar WAVs with expected-event fixtures. Blocked on soldering the
1/4" input jack.
