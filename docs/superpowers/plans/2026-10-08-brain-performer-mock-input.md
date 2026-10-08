# Brain + Performer with Mock Input — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the RMS-threshold state machine with a data-driven pet "brain" (mood + reaction picker) and "performer" (key-pose reactions, idles, eyes), driven by keyboard/scripted mock input over serial, rendered on the TFT with Evil Wizard frames as placeholder art.

**Architecture:** Hardware-free C++ in `src/core/` (MoodModel, Brain, Performer, EyeController) consumes a `MusicEvent` stream and an `ArtTables` struct; it is unit-tested under PlatformIO's `native` env with hand-written fixture tables. `tools/build_art.py` turns `art/manifest.toml` into `src/gen/pose_meta.h` (plain C++) and `src/gen/pose_pixels.h` (PROGMEM). `src/platform/` holds the only Arduino/TFT code: mock input, renderer, `main.cpp`.

**Tech Stack:** ESP32 + Arduino framework via PlatformIO, TFT_eSPI, Unity (native tests), Python 3.11+ with Pillow run via `uv`.

**Spec:** `docs/superpowers/specs/2026-10-08-reactive-pet-design.md` (sub-project 1).

---

## Environment notes (read first)

- PlatformIO CLI is `pio` (`/opt/homebrew/bin/pio`). Native tests: `pio test -e native`. Firmware build: `pio run -e esp32dev`.
- System Python has **no Pillow**. Always run Python tools through `uv`:
  - `uv run tools/build_art.py` (dependencies declared inline in the script)
  - `uv run --with pillow --with pytest pytest tools/test_build_art.py -q`
- The ESP32 board is on `/dev/cu.usbserial-10` (already in `platformio.ini`). Hardware steps are only in Task 9.
- Do **not** commit `sprites/.DS_Store` or `.DS_Store`.
- Code must compile as C++17 (we set `-std=gnu++17` for the ESP32, `-std=c++17` for native).
- Never add bob/sway/sine transforms to sprite positions (explicit user preference).

## File structure

| Path | Responsibility |
|---|---|
| `platformio.ini` | `esp32dev` env (C++17, huge_app partition) + `native` test env |
| `src/core/music_event.h` | `EventType`, `MusicEvent`, `Features`, `eventBit()` |
| `src/core/art_tables.h` | `Mood`, `Eye`, `Trigger`, priority, `PoseMeta`/`Step`/`Reaction`/`IdleLoop`/`ArtTables` |
| `src/core/rng.h` | Seeded xorshift RNG |
| `src/core/mood.h/.cpp` | Energy + mood transitions |
| `src/core/performer.h/.cpp` | Plays reaction steps, idles, interrupt rules |
| `src/core/eyes.h/.cpp` | Blink / glance scheduling |
| `src/core/brain.h/.cpp` | Wires mood → reaction picking → performer; cooldowns, variants |
| `test/fixture_art.h` | Hand-written `ArtTables` for tests |
| `test/test_types/`, `test_mood/`, `test_performer/`, `test_eyes/`, `test_brain/` | Unity tests |
| `tools/build_art.py` | Manifest → generated headers (replaces `tools/convert_sprites.py`) |
| `tools/test_build_art.py` | pytest for the builder's validation |
| `art/manifest.toml` | Placeholder wizard manifest |
| `src/gen/pose_meta.h`, `src/gen/pose_pixels.h` | Generated, committed |
| `src/platform/mock_input.h/.cpp`, `src/platform/scripts.h` | Serial keys + scripted timelines |
| `src/platform/renderer_tft.h/.cpp` | Pose + placeholder eyes + debug HUD to TFT |
| `src/platform/live_audio.h/.cpp` | Old ADC code, retained, not wired |
| `src/platform/main.cpp` | Loop: input → brain → eyes → render |
| Delete: `src/main.cpp`, `src/sprites/`, `tools/convert_sprites.py` | Superseded |

---

### Task 1: PlatformIO envs and core types

**Files:**
- Modify: `platformio.ini`
- Create: `src/core/music_event.h`, `src/core/art_tables.h`, `src/core/rng.h`
- Test: `test/test_types/test_main.cpp`

- [ ] **Step 1: Replace `platformio.ini`**

```ini
[platformio]
default_envs = esp32dev

[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
upload_port = /dev/cu.usbserial-10
monitor_port = /dev/cu.usbserial-10
board_build.partitions = huge_app.csv

lib_deps =
    bodmer/TFT_eSPI@^2.5.43

build_unflags = -std=gnu++11
build_flags =
    -std=gnu++17
    -I src
    -DUSER_SETUP_LOADED=1
    -DST7735_DRIVER=1
    -DTFT_WIDTH=128
    -DTFT_HEIGHT=160
    -DST7735_REDTAB
    -DTFT_MOSI=23
    -DTFT_SCLK=18
    -DTFT_CS=5
    -DTFT_DC=17
    -DTFT_RST=4
    -DLOAD_GLCD=1
    -DLOAD_FONT2=1
    -DSPI_FREQUENCY=27000000

[env:native]
platform = native
test_framework = unity
test_build_src = yes
build_src_filter = +<core/>
build_flags = -std=c++17 -I src -Wall
```

- [ ] **Step 2: Write the failing test** — `test/test_types/test_main.cpp`

```cpp
#include <unity.h>
#include "core/art_tables.h"
#include "core/rng.h"

void setUp() {}
void tearDown() {}

void test_rng_is_deterministic_per_seed() {
  Rng a(42), b(42), c(43);
  for (int i = 0; i < 10; i++) TEST_ASSERT_EQUAL_UINT32(a.next(), b.next());
  TEST_ASSERT_NOT_EQUAL(Rng(42).next(), c.next());
}

void test_rng_zero_seed_is_not_stuck() {
  Rng r(0);
  TEST_ASSERT_NOT_EQUAL(0, r.next());
}

void test_rng_range_is_inclusive_and_bounded() {
  Rng r(1);
  bool sawLo = false, sawHi = false;
  for (int i = 0; i < 2000; i++) {
    uint32_t v = r.range(3, 6);
    TEST_ASSERT_TRUE(v >= 3 && v <= 6);
    sawLo |= v == 3; sawHi |= v == 6;
  }
  TEST_ASSERT_TRUE(sawLo && sawHi);
  TEST_ASSERT_EQUAL_UINT32(7, r.range(7, 7));
}

void test_rng_jitter_bounds() {
  Rng r(5);
  for (int i = 0; i < 1000; i++) {
    uint32_t v = r.jitter(700, 0.2f);
    TEST_ASSERT_TRUE(v >= 560 && v <= 840);
  }
}

void test_trigger_for_event() {
  TEST_ASSERT_EQUAL_INT((int)Trigger::BigHit,  (int)triggerFor(EventType::BigHit));
  TEST_ASSERT_EQUAL_INT((int)Trigger::Cut,     (int)triggerFor(EventType::Cut));
  TEST_ASSERT_EQUAL_INT((int)Trigger::Flurry,  (int)triggerFor(EventType::Flurry));
  TEST_ASSERT_EQUAL_INT((int)Trigger::Swell,   (int)triggerFor(EventType::SwellStart));
  TEST_ASSERT_EQUAL_INT((int)Trigger::Sustain, (int)triggerFor(EventType::SustainStart));
  TEST_ASSERT_EQUAL_INT((int)Trigger::None,    (int)triggerFor(EventType::Pick));
  TEST_ASSERT_EQUAL_INT((int)Trigger::None,    (int)triggerFor(EventType::SustainEnd));
  TEST_ASSERT_EQUAL_INT((int)Trigger::None,    (int)triggerFor(EventType::SwellPeak));
}

void test_priority_order() {
  // Wake > BigHit > Cut > Flurry > Swell > Sustain > DriftOff
  TEST_ASSERT_TRUE(priority(Trigger::Wake)    > priority(Trigger::BigHit));
  TEST_ASSERT_TRUE(priority(Trigger::BigHit)  > priority(Trigger::Cut));
  TEST_ASSERT_TRUE(priority(Trigger::Cut)     > priority(Trigger::Flurry));
  TEST_ASSERT_TRUE(priority(Trigger::Flurry)  > priority(Trigger::Swell));
  TEST_ASSERT_TRUE(priority(Trigger::Swell)   > priority(Trigger::Sustain));
  TEST_ASSERT_TRUE(priority(Trigger::Sustain) > priority(Trigger::DriftOff));
}

void test_bits() {
  TEST_ASSERT_EQUAL_UINT8(1, moodBit(Mood::Asleep));
  TEST_ASSERT_EQUAL_UINT8(8, moodBit(Mood::Hyped));
  TEST_ASSERT_EQUAL_UINT16(1u << 4, eventBit(EventType::SustainEnd));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_rng_is_deterministic_per_seed);
  RUN_TEST(test_rng_zero_seed_is_not_stuck);
  RUN_TEST(test_rng_range_is_inclusive_and_bounded);
  RUN_TEST(test_rng_jitter_bounds);
  RUN_TEST(test_trigger_for_event);
  RUN_TEST(test_priority_order);
  RUN_TEST(test_bits);
  return UNITY_END();
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pio test -e native -f test_types`
Expected: compile error, `core/art_tables.h: No such file or directory`. (First run may download the `native` platform.)

- [ ] **Step 4: Create `src/core/music_event.h`**

```cpp
#pragma once
#include <stdint.h>

// Musical events produced by an input source (live detectors or mock input).
enum class EventType : uint8_t {
  Pick,          // note onset; strength 0..1 (light vs hard)
  BigHit,        // loud attack after relative quiet
  Flurry,        // sustained high onset rate (re-sent while it continues)
  SustainStart,
  SustainEnd,
  SwellStart,
  SwellPeak,
  Cut,           // sudden silence after loud playing
  None,          // sentinel: "no event" (e.g. a step without `until`)
};

struct MusicEvent { EventType type; uint32_t t_ms; float strength; };
struct Features   { float level; float onsetRate; };  // level 0..1, onsets/s

constexpr uint16_t eventBit(EventType e) { return (uint16_t)(1u << (uint8_t)e); }
```

- [ ] **Step 5: Create `src/core/art_tables.h`**

```cpp
#pragma once
#include <stdint.h>
#include "music_event.h"

enum class Mood : uint8_t { Asleep, Curious, IntoIt, Hyped };
constexpr int MOOD_COUNT = 4;
constexpr uint8_t moodBit(Mood m) { return (uint8_t)(1u << (uint8_t)m); }

// Auto = let the EyeController decide.
enum class Eye : uint8_t { Auto, Open, Blink, LookL, LookR, Wide, HappyClosed };

// Declared lowest priority first; priority() is the enum value.
enum class Trigger : uint8_t { DriftOff, Sustain, Swell, Flurry, Cut, BigHit, Wake, None };
constexpr int TRIGGER_COUNT = 7;  // excludes None

constexpr uint8_t priority(Trigger t) { return (uint8_t)t; }

inline Trigger triggerFor(EventType e) {
  switch (e) {
    case EventType::BigHit:       return Trigger::BigHit;
    case EventType::Cut:          return Trigger::Cut;
    case EventType::Flurry:       return Trigger::Flurry;
    case EventType::SwellStart:   return Trigger::Swell;
    case EventType::SustainStart: return Trigger::Sustain;
    default:                      return Trigger::None;
  }
}

constexpr uint16_t POSE_CURRENT = 0xFFFF;  // step keeps whatever pose is on screen
constexpr int8_t   EYES_BAKED   = -1;      // pose has eyes drawn in; no overlay

// Crop rect of the pose inside its 96x112 canvas, plus eye anchor (canvas coords).
struct PoseMeta { uint8_t x, y, w, h; int8_t eyeX, eyeY; };

struct Step {
  uint16_t  pose;               // pose index or POSE_CURRENT
  uint16_t  holdMin, holdMax;   // ms; picked uniformly each play
  Eye       eyes;
  EventType until;              // EventType::None = no wait
  uint16_t  untilMax;           // ms from step start
};

struct Reaction {
  Trigger  trigger;
  uint8_t  moodMask;            // 0 = any mood, else OR of moodBit()
  uint16_t cooldownMs;
  uint16_t firstStep;           // index into ArtTables::steps
  uint8_t  stepCount;
};

struct IdleLoop { uint16_t first; uint8_t count; };  // slice of idlePoses

struct ArtTables {
  const PoseMeta* poses;     uint16_t poseCount;
  const Step*     steps;     uint16_t stepCount;
  const Reaction* reactions; uint8_t  reactionCount;
  const uint16_t* idlePoses;
  IdleLoop        idles[MOOD_COUNT];  // indexed by Mood
};
```

- [ ] **Step 6: Create `src/core/rng.h`**

```cpp
#pragma once
#include <stdint.h>

// xorshift32 — small, deterministic per seed (tests pass fixed seeds).
class Rng {
 public:
  explicit Rng(uint32_t seed) : s_(seed ? seed : 0x9E3779B9u) {}
  uint32_t next() { s_ ^= s_ << 13; s_ ^= s_ >> 17; s_ ^= s_ << 5; return s_; }
  // Uniform in [lo, hi], inclusive.
  uint32_t range(uint32_t lo, uint32_t hi) { return hi <= lo ? lo : lo + next() % (hi - lo + 1); }
  // v ± pct (pct in 0..1).
  uint32_t jitter(uint32_t v, float pct) { uint32_t d = (uint32_t)(v * pct); return range(v - d, v + d); }
 private:
  uint32_t s_;
};
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pio test -e native -f test_types`
Expected: `7 Tests 0 Failures 0 Ignored`, PASSED.

- [ ] **Step 8: Check the firmware still builds** (old `src/main.cpp` is untouched; core headers are unused by it)

Run: `pio run -e esp32dev`
Expected: `SUCCESS`.

- [ ] **Step 9: Commit**

```bash
git add platformio.ini src/core test/test_types
git commit -m "Add core types, RNG and native test env

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: MoodModel

**Files:**
- Create: `src/core/mood.h`, `src/core/mood.cpp`
- Test: `test/test_mood/test_main.cpp`

- [ ] **Step 1: Write the failing test** — `test/test_mood/test_main.cpp`

```cpp
#include <unity.h>
#include "core/mood.h"

#define ASSERT_MOOD(expected) TEST_ASSERT_EQUAL_INT((int)(expected), (int)m.mood())

static MoodModel m;
static uint32_t t;

void setUp() { m = MoodModel(); t = 0; m.reset(t); }
void tearDown() {}

// Tick at 100 Hz for `ms` with a constant level.
static void run(float level, uint32_t ms) {
  for (uint32_t i = 0; i < ms; i += 10) { t += 10; m.tick({level, 0}, t); }
}
static MusicEvent ev(EventType type, float strength = 1.0f) { return {type, t, strength}; }
static void wake() { m.onEvent(ev(EventType::Pick), t); }

void test_starts_asleep_with_zero_energy() {
  ASSERT_MOOD(Mood::Asleep);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, m.energy());
}

void test_event_wakes_immediately_and_is_consumed() {
  TEST_ASSERT_EQUAL_INT((int)MoodChange::Woke, (int)m.onEvent(ev(EventType::BigHit), t));
  ASSERT_MOOD(Mood::Curious);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, m.energy());  // boost not applied
}

void test_level_does_not_wake() {
  run(1.0f, 5000);
  ASSERT_MOOD(Mood::Asleep);
}

void test_event_boosts_energy() {
  wake();
  m.onEvent(ev(EventType::BigHit), t);
  TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.2f, m.energy());
  m.onEvent(ev(EventType::Flurry), t);
  TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.3f, m.energy());
  m.onEvent(ev(EventType::Pick, 0.5f), t);
  TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.315f, m.energy());
  for (int i = 0; i < 10; i++) m.onEvent(ev(EventType::BigHit), t);
  TEST_ASSERT_EQUAL_FLOAT(1.0f, m.energy());
}

void test_energy_attacks_toward_level() {
  wake();
  run(0.5f, 1000);
  TEST_ASSERT_FLOAT_WITHIN(0.02f, 0.5f, m.energy());
}

void test_energy_decays_with_tau() {
  wake();
  run(1.0f, 500);
  float e0 = m.energy();
  run(0.0f, 8000);  // one time constant
  TEST_ASSERT_FLOAT_WITHIN(0.01f, e0 * 0.3679f, m.energy());
}

void test_dwell_then_hysteresis_into_it() {
  wake();
  run(0.5f, 1500);
  ASSERT_MOOD(Mood::Curious);   // energy high enough, but dwell not met
  run(0.5f, 600);
  ASSERT_MOOD(Mood::IntoIt);
  run(0.3f, 20000);
  ASSERT_MOOD(Mood::IntoIt);    // 0.3 is above the 0.25 down-threshold
  run(0.2f, 10000);
  ASSERT_MOOD(Mood::Curious);
}

void test_hyped_and_back() {
  wake();
  run(1.0f, 4500);
  ASSERT_MOOD(Mood::Hyped);
  run(0.6f, 10000);
  ASSERT_MOOD(Mood::Hyped);     // 0.6 is above the 0.55 down-threshold
  run(0.4f, 10000);
  ASSERT_MOOD(Mood::IntoIt);
}

void test_wind_down_passes_through_each_mood() {
  wake();
  run(1.0f, 4500);
  ASSERT_MOOD(Mood::Hyped);
  Mood seen[8]; int n = 0;
  uint32_t curiousAt = 0, asleepAt = 0;
  for (uint32_t i = 0; i < 60000 && m.mood() != Mood::Asleep; i += 10) {
    t += 10;
    MoodChange c = m.tick({0.0f, 0}, t);
    if (c == MoodChange::None) continue;
    seen[n++] = m.mood();
    if (m.mood() == Mood::Curious) curiousAt = t;
    if (c == MoodChange::FellAsleep) asleepAt = t;
  }
  TEST_ASSERT_EQUAL_INT(3, n);
  TEST_ASSERT_EQUAL_INT((int)Mood::IntoIt,  (int)seen[0]);
  TEST_ASSERT_EQUAL_INT((int)Mood::Curious, (int)seen[1]);
  TEST_ASSERT_EQUAL_INT((int)Mood::Asleep,  (int)seen[2]);
  TEST_ASSERT_TRUE(asleepAt - curiousAt >= 10000 && asleepAt - curiousAt <= 10010);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, m.energy());
}

void test_quiet_playing_keeps_it_awake() {
  wake();
  run(0.05f, 30000);   // above the 0.03 noise floor
  ASSERT_MOOD(Mood::Curious);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_starts_asleep_with_zero_energy);
  RUN_TEST(test_event_wakes_immediately_and_is_consumed);
  RUN_TEST(test_level_does_not_wake);
  RUN_TEST(test_event_boosts_energy);
  RUN_TEST(test_energy_attacks_toward_level);
  RUN_TEST(test_energy_decays_with_tau);
  RUN_TEST(test_dwell_then_hysteresis_into_it);
  RUN_TEST(test_hyped_and_back);
  RUN_TEST(test_wind_down_passes_through_each_mood);
  RUN_TEST(test_quiet_playing_keeps_it_awake);
  return UNITY_END();
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pio test -e native -f test_mood`
Expected: compile error, `core/mood.h: No such file or directory`.

- [ ] **Step 3: Create `src/core/mood.h`**

```cpp
#pragma once
#include <stdint.h>
#include "art_tables.h"
#include "music_event.h"

struct MoodConfig {
  float    kAttack     = 0.3f;    // per 10 ms tick
  float    tauS        = 8.0f;    // energy release time constant
  float    boostBigHit = 0.2f;
  float    boostFlurry = 0.1f;
  float    boostPick   = 0.03f;   // × strength
  float    intoItUp    = 0.35f, intoItDown = 0.25f;
  float    hypedUp     = 0.70f, hypedDown  = 0.55f;
  uint32_t dwellMs     = 2000;    // threshold-driven transitions only
  float    noiseFloor  = 0.03f;
  uint32_t silenceMs   = 10000;   // Curious → Asleep
};

enum class MoodChange : uint8_t { None, Changed, Woke, FellAsleep };

class MoodModel {
 public:
  explicit MoodModel(const MoodConfig& cfg = MoodConfig()) : cfg_(cfg) {}
  void       reset(uint32_t now);                          // → Asleep, energy 0
  MoodChange onEvent(const MusicEvent& e, uint32_t now);   // Woke if it was asleep
  MoodChange tick(const Features& f, uint32_t now);        // call every ~10 ms
  Mood  mood()   const { return mood_; }
  float energy() const { return energy_; }

 private:
  void setMood(Mood m, uint32_t now);

  MoodConfig cfg_;
  Mood     mood_        = Mood::Asleep;
  float    energy_      = 0;
  uint32_t moodSince_   = 0;
  uint32_t silentSince_ = 0;
  uint32_t lastTick_    = 0;
};
```

- [ ] **Step 4: Create `src/core/mood.cpp`**

```cpp
#include "mood.h"
#include <math.h>

void MoodModel::reset(uint32_t now) {
  mood_ = Mood::Asleep;
  energy_ = 0;
  moodSince_ = silentSince_ = lastTick_ = now;
}

void MoodModel::setMood(Mood m, uint32_t now) {
  mood_ = m;
  moodSince_ = now;
  silentSince_ = now;  // silence timer restarts on every mood change
}

MoodChange MoodModel::onEvent(const MusicEvent& e, uint32_t now) {
  if (mood_ == Mood::Asleep) {
    setMood(Mood::Curious, now);
    return MoodChange::Woke;  // event consumed: no boost, no reaction of its own
  }
  float boost = 0;
  switch (e.type) {
    case EventType::BigHit: boost = cfg_.boostBigHit; break;
    case EventType::Flurry: boost = cfg_.boostFlurry; break;
    case EventType::Pick:   boost = cfg_.boostPick * e.strength; break;
    default: break;
  }
  energy_ = fminf(1.0f, energy_ + boost);
  return MoodChange::None;
}

MoodChange MoodModel::tick(const Features& f, uint32_t now) {
  float dt = (now - lastTick_) / 1000.0f;
  lastTick_ = now;
  if (f.level > energy_) energy_ += (f.level - energy_) * cfg_.kAttack;
  energy_ *= expf(-dt / cfg_.tauS);
  energy_ = fmaxf(0.0f, fminf(1.0f, energy_));
  if (f.level >= cfg_.noiseFloor) silentSince_ = now;

  if (mood_ == Mood::Asleep) return MoodChange::None;

  if (mood_ == Mood::Curious && now - silentSince_ >= cfg_.silenceMs) {
    setMood(Mood::Asleep, now);
    energy_ = 0;
    return MoodChange::FellAsleep;
  }

  if (now - moodSince_ < cfg_.dwellMs) return MoodChange::None;

  Mood target = mood_;
  switch (mood_) {
    case Mood::Curious:
      if (energy_ >= cfg_.intoItUp) target = Mood::IntoIt;
      break;
    case Mood::IntoIt:
      if (energy_ >= cfg_.hypedUp) target = Mood::Hyped;
      else if (energy_ < cfg_.intoItDown) target = Mood::Curious;
      break;
    case Mood::Hyped:
      if (energy_ < cfg_.hypedDown) target = Mood::IntoIt;
      break;
    default:
      break;
  }
  if (target == mood_) return MoodChange::None;
  setMood(target, now);
  return MoodChange::Changed;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pio test -e native -f test_mood`
Expected: `10 Tests 0 Failures`.

- [ ] **Step 6: Commit**

```bash
git add src/core/mood.h src/core/mood.cpp test/test_mood
git commit -m "Add MoodModel: energy envelope, hysteresis, sleep/wake

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Test fixture art tables

**Files:**
- Create: `test/fixture_art.h`

- [ ] **Step 1: Create `test/fixture_art.h`** (used by Tasks 4 and 6; PlatformIO does not build files in the `test/` root, it only includes them)

```cpp
#pragma once
#include "core/art_tables.h"

// Poses 0..9; geometry is irrelevant to core logic.
// Idles: Asleep {0}, Curious {1,2}, IntoIt {3,4}, Hyped {5,6}.
static const PoseMeta FX_POSES[10] = {};

static const Step FX_STEPS[] = {
  // 0-1: BigHit (any mood) — 480 ms total
  {7,  80,  80, Eye::Wide, EventType::None, 0},
  {8, 400, 400, Eye::Auto, EventType::None, 0},
  // 2: BigHit (Hyped only)
  {9, 100, 100, Eye::Auto, EventType::None, 0},
  // 3-5: Sustain — middle step waits for SustainEnd (cap 1000 ms)
  {7, 100, 100, Eye::Auto, EventType::None, 0},
  {8, 200, 200, Eye::Auto, EventType::SustainEnd, 1000},
  {9, 100, 100, Eye::Auto, EventType::None, 0},
  // 6-7: Cut — freezes the current pose first
  {POSE_CURRENT, 300, 300, Eye::Auto, EventType::None, 0},
  {9, 200, 200, Eye::Auto, EventType::None, 0},
  // 8: Flurry
  {7, 300, 300, Eye::Auto, EventType::None, 0},
  // 9: Wake
  {7, 500, 500, Eye::Wide, EventType::None, 0},
  // 10: DriftOff
  {8, 500, 500, Eye::Auto, EventType::None, 0},
  // 11: Swell — random hold
  {7, 100, 300, Eye::Auto, EventType::None, 0},
};

enum FxReaction { FX_BIGHIT, FX_BIGHIT_HYPED, FX_SUSTAIN, FX_CUT, FX_FLURRY, FX_WAKE, FX_DRIFTOFF, FX_SWELL };

static const Reaction FX_REACTIONS[] = {
  {Trigger::BigHit,   0,                    1500, 0,  2},
  {Trigger::BigHit,   moodBit(Mood::Hyped), 1500, 2,  1},
  {Trigger::Sustain,  0,                    1500, 3,  3},
  {Trigger::Cut,      0,                    1500, 6,  2},
  {Trigger::Flurry,   0,                    1500, 8,  1},
  {Trigger::Wake,     0,                    1500, 9,  1},
  {Trigger::DriftOff, 0,                    1500, 10, 1},
  {Trigger::Swell,    0,                    1500, 11, 1},
};

static const uint16_t FX_IDLE_POSES[] = {0, 1, 2, 3, 4, 5, 6};

static const ArtTables FX_ART = {
  FX_POSES, 10,
  FX_STEPS, sizeof(FX_STEPS) / sizeof(FX_STEPS[0]),
  FX_REACTIONS, sizeof(FX_REACTIONS) / sizeof(FX_REACTIONS[0]),
  FX_IDLE_POSES,
  {{0, 1}, {1, 2}, {3, 2}, {5, 2}},
};
```

- [ ] **Step 2: Commit**

```bash
git add test/fixture_art.h
git commit -m "Add fixture art tables for core tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Performer

**Files:**
- Create: `src/core/performer.h`, `src/core/performer.cpp`
- Test: `test/test_performer/test_main.cpp`

- [ ] **Step 1: Write the failing test** — `test/test_performer/test_main.cpp`

```cpp
#include <unity.h>
#include "core/performer.h"
#include "../fixture_art.h"

static Rng rng(1);
static Performer* p = nullptr;
static uint32_t t;

void setUp() {
  rng = Rng(1);
  delete p;
  p = new Performer(FX_ART, rng);
  t = 0;
  p->reset(Mood::Curious, t);
}
void tearDown() {}

static void run(Mood m, uint32_t ms) {
  for (uint32_t i = 0; i < ms; i += 10) { t += 10; p->tick(m, t); }
}

// --- reactions ---------------------------------------------------------------

void test_reaction_plays_steps_then_returns_to_idle() {
  p->start(FX_BIGHIT, Trigger::BigHit, t);
  TEST_ASSERT_TRUE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(7, p->pose());
  TEST_ASSERT_EQUAL_INT((int)Eye::Wide, (int)p->eyes());
  run(Mood::Curious, 80);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());
  TEST_ASSERT_EQUAL_INT((int)Eye::Auto, (int)p->eyes());
  TEST_ASSERT_EQUAL_UINT8(1, p->step());
  run(Mood::Curious, 400);
  TEST_ASSERT_FALSE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());  // Curious idle, pose 0
}

void test_until_holds_until_event() {
  p->start(FX_SUSTAIN, Trigger::Sustain, t);
  run(Mood::Curious, 100);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());
  run(Mood::Curious, 500);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());  // still waiting
  p->onEvent(EventType::SustainEnd);
  run(Mood::Curious, 10);
  TEST_ASSERT_EQUAL_UINT16(9, p->pose());
}

void test_until_cap_expires_and_continues() {
  p->start(FX_SUSTAIN, Trigger::Sustain, t);
  run(Mood::Curious, 100);
  run(Mood::Curious, 1000);  // untilMax
  TEST_ASSERT_TRUE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(9, p->pose());
}

void test_until_event_before_step_plays_min_hold() {
  p->start(FX_SUSTAIN, Trigger::Sustain, t);
  p->onEvent(EventType::SustainEnd);  // arrives during step 0
  run(Mood::Curious, 100);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());
  run(Mood::Curious, 200);
  TEST_ASSERT_EQUAL_UINT16(9, p->pose());
}

void test_pose_current_freezes_previous_pose() {
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());
  p->start(FX_CUT, Trigger::Cut, t);
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());
  run(Mood::Curious, 300);
  TEST_ASSERT_EQUAL_UINT16(9, p->pose());
}

void test_random_hold_within_range() {
  for (uint32_t seed = 1; seed <= 20; seed++) {
    rng = Rng(seed);
    uint32_t start = t;
    p->start(FX_SWELL, Trigger::Swell, t);
    while (p->playing() && t - start < 1000) run(Mood::Curious, 10);
    uint32_t took = t - start;
    TEST_ASSERT_TRUE_MESSAGE(took >= 100 && took <= 310, "hold outside [100,300]");
  }
}

// --- interrupts --------------------------------------------------------------

void test_interrupt_guard_120ms_from_reaction_start() {
  p->start(FX_SUSTAIN, Trigger::Sustain, t);
  TEST_ASSERT_FALSE(p->canInterrupt(Trigger::BigHit, t));
  run(Mood::Curious, 110);
  TEST_ASSERT_FALSE(p->canInterrupt(Trigger::BigHit, t));
  run(Mood::Curious, 10);
  TEST_ASSERT_TRUE(p->canInterrupt(Trigger::BigHit, t));
}

void test_equal_or_lower_priority_cannot_interrupt() {
  p->start(FX_CUT, Trigger::Cut, t);
  run(Mood::Curious, 200);
  TEST_ASSERT_FALSE(p->canInterrupt(Trigger::Flurry, t));
  TEST_ASSERT_FALSE(p->canInterrupt(Trigger::Cut, t));
}

void test_wake_uninterruptible_driftoff_always_interruptible() {
  p->start(FX_WAKE, Trigger::Wake, t);
  run(Mood::Curious, 300);
  TEST_ASSERT_FALSE(p->canInterrupt(Trigger::BigHit, t));
  p->start(FX_DRIFTOFF, Trigger::DriftOff, t);
  TEST_ASSERT_TRUE(p->canInterrupt(Trigger::Sustain, t));
}

void test_idle_can_always_be_interrupted() {
  TEST_ASSERT_TRUE(p->canInterrupt(Trigger::DriftOff, t));
}

void test_extend_restarts_current_step_hold() {
  p->start(FX_FLURRY, Trigger::Flurry, t);
  run(Mood::Curious, 200);
  p->extend(t);
  run(Mood::Curious, 200);
  TEST_ASSERT_TRUE(p->playing());
  run(Mood::Curious, 100);
  TEST_ASSERT_FALSE(p->playing());
}

// --- idles -------------------------------------------------------------------

void test_curious_idle_advances_on_timer() {
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());
  run(Mood::Curious, 850);  // 700 ms ± 20 %
  TEST_ASSERT_EQUAL_UINT16(2, p->pose());
}

void test_mood_change_switches_idle_immediately() {
  run(Mood::IntoIt, 10);
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
}

void test_strong_pick_beat_steps_with_min_gap() {
  p->reset(Mood::IntoIt, t);
  t += 300; p->onPick(0.9f, t);
  TEST_ASSERT_EQUAL_UINT16(4, p->pose());
  t += 100; p->onPick(0.9f, t);
  TEST_ASSERT_EQUAL_UINT16(4, p->pose());  // < 250 ms since last step
  t += 200; p->onPick(0.9f, t);
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
}

void test_weak_picks_step_every_second_pick() {
  p->reset(Mood::IntoIt, t);
  t += 300; p->onPick(0.2f, t);
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
  t += 300; p->onPick(0.2f, t);
  TEST_ASSERT_EQUAL_UINT16(4, p->pose());
}

void test_picks_do_not_step_curious_idle() {
  t += 300; p->onPick(0.9f, t);
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());
}

void test_beat_idle_falls_back_to_timer() {
  p->reset(Mood::IntoIt, t);
  run(Mood::IntoIt, 1490);
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
  run(Mood::IntoIt, 20);   // 1.5 s without a step
  TEST_ASSERT_EQUAL_UINT16(4, p->pose());
  run(Mood::IntoIt, 500);  // IntoIt timer period
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
}

void test_no_beat_step_during_reaction() {
  p->reset(Mood::IntoIt, t);
  p->start(FX_BIGHIT, Trigger::BigHit, t);
  t += 300; p->onPick(0.9f, t);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());
  run(Mood::IntoIt, 200);
  TEST_ASSERT_FALSE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
}

void test_reaction_ends_into_new_moods_idle_at_pose_0() {
  run(Mood::Curious, 850);
  TEST_ASSERT_EQUAL_UINT16(2, p->pose());
  p->start(FX_BIGHIT, Trigger::BigHit, t);
  run(Mood::Hyped, 480);   // mood changed mid-reaction
  TEST_ASSERT_FALSE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(5, p->pose());
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_reaction_plays_steps_then_returns_to_idle);
  RUN_TEST(test_until_holds_until_event);
  RUN_TEST(test_until_cap_expires_and_continues);
  RUN_TEST(test_until_event_before_step_plays_min_hold);
  RUN_TEST(test_pose_current_freezes_previous_pose);
  RUN_TEST(test_random_hold_within_range);
  RUN_TEST(test_interrupt_guard_120ms_from_reaction_start);
  RUN_TEST(test_equal_or_lower_priority_cannot_interrupt);
  RUN_TEST(test_wake_uninterruptible_driftoff_always_interruptible);
  RUN_TEST(test_idle_can_always_be_interrupted);
  RUN_TEST(test_extend_restarts_current_step_hold);
  RUN_TEST(test_curious_idle_advances_on_timer);
  RUN_TEST(test_mood_change_switches_idle_immediately);
  RUN_TEST(test_strong_pick_beat_steps_with_min_gap);
  RUN_TEST(test_weak_picks_step_every_second_pick);
  RUN_TEST(test_picks_do_not_step_curious_idle);
  RUN_TEST(test_beat_idle_falls_back_to_timer);
  RUN_TEST(test_no_beat_step_during_reaction);
  RUN_TEST(test_reaction_ends_into_new_moods_idle_at_pose_0);
  return UNITY_END();
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pio test -e native -f test_performer`
Expected: compile error, `core/performer.h: No such file or directory`.

- [ ] **Step 3: Create `src/core/performer.h`**

```cpp
#pragma once
#include <stdint.h>
#include "art_tables.h"
#include "rng.h"

struct PerformerConfig {
  uint32_t interruptGuardMs = 120;
  uint32_t asleepIdleMs     = 900;   // ±20 % jitter
  uint32_t curiousIdleMs    = 700;   // ±20 % jitter
  uint32_t intoItIdleMs     = 500;   // timer fallback period
  uint32_t hypedIdleMs      = 400;   // timer fallback period
  uint32_t beatFallbackMs   = 1500;  // no beat-step for this long → timer
  uint32_t beatMinGapMs     = 250;
  float    strongPick       = 0.5f;
};

// Plays reactions (sequences of key poses) and mood idles. Decides nothing
// about *which* reaction — that is the Brain's job.
class Performer {
 public:
  Performer(const ArtTables& art, Rng& rng, const PerformerConfig& cfg = PerformerConfig())
      : art_(art), rng_(rng), cfg_(cfg) {}

  void reset(Mood mood, uint32_t now);

  bool     playing()  const { return reaction_ >= 0; }
  int      reaction() const { return reaction_; }
  Trigger  trigger()  const { return trigger_; }
  uint8_t  step()     const { return step_; }
  uint16_t pose()     const { return pose_; }
  Eye      eyes()     const { return eyes_; }   // Auto unless a step overrides

  bool canInterrupt(Trigger t, uint32_t now) const;
  void start(int reaction, Trigger t, uint32_t now);
  void extend(uint32_t now);                  // restart current step's hold
  void onEvent(EventType e);                  // feeds `until`
  void onPick(float strength, uint32_t now);  // beat-step idle
  void tick(Mood mood, uint32_t now);

 private:
  void     enterStep(uint8_t i, uint32_t now);
  void     startIdle(Mood mood, uint32_t now);
  void     advanceIdle(uint32_t now);
  uint32_t periodFor(Mood m);

  const ArtTables& art_;
  Rng&             rng_;
  PerformerConfig  cfg_;

  int      reaction_      = -1;
  Trigger  trigger_       = Trigger::None;
  uint8_t  step_          = 0;
  uint32_t reactionStart_ = 0;
  uint32_t stepStart_     = 0;
  uint32_t stepHold_      = 0;
  uint16_t seen_          = 0;   // eventBit()s seen since reaction start

  uint16_t pose_ = 0;
  Eye      eyes_ = Eye::Auto;

  Mood     idleMood_     = Mood::Asleep;
  uint8_t  idleIdx_      = 0;
  uint8_t  picks_        = 0;
  uint32_t lastIdleStep_ = 0;
  uint32_t lastBeat_     = 0;
  uint32_t idlePeriod_   = 0;
};
```

- [ ] **Step 4: Create `src/core/performer.cpp`**

```cpp
#include "performer.h"

void Performer::reset(Mood mood, uint32_t now) {
  reaction_ = -1;
  trigger_ = Trigger::None;
  startIdle(mood, now);
}

bool Performer::canInterrupt(Trigger t, uint32_t now) const {
  if (!playing()) return true;
  if (trigger_ == Trigger::Wake) return false;
  if (trigger_ == Trigger::DriftOff) return true;
  if (priority(t) <= priority(trigger_)) return false;
  return now - reactionStart_ >= cfg_.interruptGuardMs;
}

void Performer::start(int reaction, Trigger t, uint32_t now) {
  reaction_ = reaction;
  trigger_ = t;
  reactionStart_ = now;
  seen_ = 0;
  enterStep(0, now);
}

void Performer::extend(uint32_t now) {
  if (playing()) stepStart_ = now;
}

void Performer::onEvent(EventType e) {
  if (playing()) seen_ |= eventBit(e);
}

void Performer::onPick(float strength, uint32_t now) {
  if (playing()) return;
  if (idleMood_ != Mood::IntoIt && idleMood_ != Mood::Hyped) return;
  picks_++;
  bool qualifies = strength >= cfg_.strongPick || picks_ >= 2;
  if (!qualifies || now - lastIdleStep_ < cfg_.beatMinGapMs) return;
  advanceIdle(now);
  lastBeat_ = now;
  picks_ = 0;
}

void Performer::tick(Mood mood, uint32_t now) {
  if (playing()) {
    const Reaction& r = art_.reactions[reaction_];
    const Step& s = art_.steps[r.firstStep + step_];
    uint32_t elapsed = now - stepStart_;
    if (elapsed < stepHold_) return;
    bool waiting = s.until != EventType::None && !(seen_ & eventBit(s.until));
    if (waiting && elapsed < s.untilMax) return;
    if (step_ + 1 < r.stepCount) { enterStep(step_ + 1, now); return; }
    reaction_ = -1;
    trigger_ = Trigger::None;
    startIdle(mood, now);
    return;
  }
  if (mood != idleMood_) { startIdle(mood, now); return; }
  bool beat = mood == Mood::IntoIt || mood == Mood::Hyped;
  if (beat && now - lastBeat_ < cfg_.beatFallbackMs) return;
  if (now - lastIdleStep_ >= idlePeriod_) advanceIdle(now);
}

void Performer::enterStep(uint8_t i, uint32_t now) {
  const Step& s = art_.steps[art_.reactions[reaction_].firstStep + i];
  step_ = i;
  stepStart_ = now;
  stepHold_ = rng_.range(s.holdMin, s.holdMax);
  if (s.pose != POSE_CURRENT) pose_ = s.pose;
  eyes_ = s.eyes;
}

void Performer::startIdle(Mood mood, uint32_t now) {
  idleMood_ = mood;
  idleIdx_ = 0;
  picks_ = 0;
  pose_ = art_.idlePoses[art_.idles[(int)mood].first];
  eyes_ = Eye::Auto;
  lastIdleStep_ = lastBeat_ = now;
  idlePeriod_ = periodFor(mood);
}

void Performer::advanceIdle(uint32_t now) {
  const IdleLoop& l = art_.idles[(int)idleMood_];
  idleIdx_ = (idleIdx_ + 1) % l.count;
  pose_ = art_.idlePoses[l.first + idleIdx_];
  lastIdleStep_ = now;
  idlePeriod_ = periodFor(idleMood_);
}

uint32_t Performer::periodFor(Mood m) {
  switch (m) {
    case Mood::Asleep:  return rng_.jitter(cfg_.asleepIdleMs, 0.2f);
    case Mood::Curious: return rng_.jitter(cfg_.curiousIdleMs, 0.2f);
    case Mood::IntoIt:  return cfg_.intoItIdleMs;
    default:            return cfg_.hypedIdleMs;
  }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pio test -e native -f test_performer`
Expected: `19 Tests 0 Failures`.

- [ ] **Step 6: Commit**

```bash
git add src/core/performer.h src/core/performer.cpp test/test_performer
git commit -m "Add Performer: reaction steps, until/holds, interrupts, beat-step idles

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: EyeController

**Files:**
- Create: `src/core/eyes.h`, `src/core/eyes.cpp`
- Test: `test/test_eyes/test_main.cpp`

- [ ] **Step 1: Write the failing test** — `test/test_eyes/test_main.cpp`

```cpp
#include <unity.h>
#include "core/eyes.h"

static Rng rng(3);
static EyeController* eyes = nullptr;
static uint32_t t;

void setUp() {
  rng = Rng(3);
  delete eyes;
  eyes = new EyeController(rng);
  t = 0;
  eyes->reset(t);
}
void tearDown() {}

static void step(Mood m, Eye override = Eye::Auto) { t += 10; eyes->tick(m, override, t); }

void test_first_blink_in_window_and_lasts_120ms() {
  while (eyes->eye() != Eye::Blink && t < 8000) step(Mood::Curious);
  // Due at 2000-6000 ms; a glance in progress can delay it by up to 800 ms.
  TEST_ASSERT_TRUE(t >= 2000 && t <= 6810);
  uint32_t start = t;
  while (eyes->eye() == Eye::Blink) step(Mood::Curious);
  TEST_ASSERT_EQUAL_UINT32(120, t - start);
}

void test_glance_happens() {
  bool glanced = false;
  while (t < 10500) {
    step(Mood::Curious);
    glanced |= eyes->eye() == Eye::LookL || eyes->eye() == Eye::LookR;
  }
  TEST_ASSERT_TRUE(glanced);
}

void test_step_override_wins() {
  step(Mood::Curious, Eye::Wide);
  TEST_ASSERT_EQUAL_INT((int)Eye::Wide, (int)eyes->eye());
}

void test_off_while_asleep_and_rescheduled_on_wake() {
  while (t < 20000) {
    step(Mood::Asleep);
    TEST_ASSERT_EQUAL_INT((int)Eye::Open, (int)eyes->eye());
  }
  uint32_t woke = t;
  while (t < woke + 1990) {
    step(Mood::Curious);
    TEST_ASSERT_EQUAL_INT((int)Eye::Open, (int)eyes->eye());
  }
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_first_blink_in_window_and_lasts_120ms);
  RUN_TEST(test_glance_happens);
  RUN_TEST(test_step_override_wins);
  RUN_TEST(test_off_while_asleep_and_rescheduled_on_wake);
  return UNITY_END();
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pio test -e native -f test_eyes`
Expected: compile error, `core/eyes.h: No such file or directory`.

- [ ] **Step 3: Create `src/core/eyes.h`**

```cpp
#pragma once
#include <stdint.h>
#include "art_tables.h"
#include "rng.h"

struct EyeConfig {
  uint32_t blinkMs       = 120;
  uint32_t blinkEveryMin = 2000, blinkEveryMax  = 6000;
  uint32_t glanceEveryMin = 4000, glanceEveryMax = 10000;
  uint32_t glanceMin     = 400,  glanceMax      = 800;
};

// Small, deliberate eye changes (blink, glance) that keep holds alive.
class EyeController {
 public:
  explicit EyeController(Rng& rng, const EyeConfig& cfg = EyeConfig()) : rng_(rng), cfg_(cfg) {}
  void reset(uint32_t now);
  void tick(Mood mood, Eye stepOverride, uint32_t now);
  Eye  eye() const { return eye_; }

 private:
  void schedule(uint32_t now);
  static bool due(uint32_t now, uint32_t at) { return (int32_t)(now - at) >= 0; }

  Rng&      rng_;
  EyeConfig cfg_;
  Eye       eye_        = Eye::Open;
  Eye       action_     = Eye::Open;  // Open, Blink, LookL or LookR
  uint32_t  actionEnd_  = 0;
  uint32_t  nextBlink_  = 0;
  uint32_t  nextGlance_ = 0;
  bool      asleep_     = false;
};
```

- [ ] **Step 4: Create `src/core/eyes.cpp`**

```cpp
#include "eyes.h"

void EyeController::reset(uint32_t now) {
  asleep_ = false;
  eye_ = Eye::Open;
  schedule(now);
}

void EyeController::schedule(uint32_t now) {
  action_ = Eye::Open;
  nextBlink_ = now + rng_.range(cfg_.blinkEveryMin, cfg_.blinkEveryMax);
  nextGlance_ = now + rng_.range(cfg_.glanceEveryMin, cfg_.glanceEveryMax);
}

void EyeController::tick(Mood mood, Eye stepOverride, uint32_t now) {
  if (mood == Mood::Asleep) {  // Asleep poses have baked eyes
    asleep_ = true;
    eye_ = Eye::Open;
    return;
  }
  if (asleep_) { asleep_ = false; schedule(now); }

  if (action_ != Eye::Open && due(now, actionEnd_)) action_ = Eye::Open;
  if (action_ == Eye::Open) {
    if (due(now, nextBlink_)) {
      action_ = Eye::Blink;
      actionEnd_ = now + cfg_.blinkMs;
      nextBlink_ = now + rng_.range(cfg_.blinkEveryMin, cfg_.blinkEveryMax);
    } else if (due(now, nextGlance_)) {
      action_ = rng_.range(0, 1) ? Eye::LookL : Eye::LookR;
      actionEnd_ = now + rng_.range(cfg_.glanceMin, cfg_.glanceMax);
      nextGlance_ = now + rng_.range(cfg_.glanceEveryMin, cfg_.glanceEveryMax);
    }
  }
  eye_ = stepOverride != Eye::Auto ? stepOverride : action_;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pio test -e native -f test_eyes`
Expected: `4 Tests 0 Failures`.

- [ ] **Step 6: Commit**

```bash
git add src/core/eyes.h src/core/eyes.cpp test/test_eyes
git commit -m "Add EyeController: blink and glance scheduling

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Brain (picker, cooldowns, wiring)

**Files:**
- Create: `src/core/brain.h`, `src/core/brain.cpp`
- Test: `test/test_brain/test_main.cpp`

- [ ] **Step 1: Write the failing test** — `test/test_brain/test_main.cpp`

```cpp
#include <unity.h>
#include "core/brain.h"
#include "../fixture_art.h"

static Rng rng(7);
static Performer* perf = nullptr;
static Brain* brain = nullptr;
static uint32_t t;

void setUp() {
  delete brain;
  delete perf;
  rng = Rng(7);
  t = 0;
  perf = new Performer(FX_ART, rng);
  brain = new Brain(FX_ART, rng, *perf);
  brain->reset(t);
}
void tearDown() {}

static void run(float level, uint32_t ms) {
  for (uint32_t i = 0; i < ms; i += 10) { t += 10; brain->tick({level, 0}, t); }
}
static void send(EventType e, float strength = 1.0f) { brain->onEvent({e, t, strength}, t); }
static void wakeAndSettle() { send(EventType::Pick); run(0.0f, 600); }  // Wake is 500 ms

void test_event_while_asleep_plays_wake_only() {
  send(EventType::BigHit);
  TEST_ASSERT_EQUAL_INT((int)Mood::Curious, (int)brain->mood());
  TEST_ASSERT_EQUAL_INT(FX_WAKE, perf->reaction());
  TEST_ASSERT_EQUAL_FLOAT(0.0f, brain->energy());
}

void test_reaction_respects_mood_filter() {
  wakeAndSettle();
  send(EventType::BigHit);
  TEST_ASSERT_EQUAL_INT(FX_BIGHIT, perf->reaction());  // Hyped-only variant excluded
}

void test_variants_never_repeat_back_to_back() {
  wakeAndSettle();
  run(1.0f, 4500);
  TEST_ASSERT_EQUAL_INT((int)Mood::Hyped, (int)brain->mood());
  int prev = -1;
  for (int i = 0; i < 6; i++) {
    send(EventType::BigHit);
    int r = perf->reaction();
    TEST_ASSERT_TRUE(r == FX_BIGHIT || r == FX_BIGHIT_HYPED);
    TEST_ASSERT_NOT_EQUAL(prev, r);
    prev = r;
    run(1.0f, 1600);  // past cooldown and reaction end
  }
}

void test_cooldown_from_reaction_start() {
  wakeAndSettle();
  send(EventType::BigHit);
  run(0.0f, 600);
  TEST_ASSERT_FALSE(perf->playing());
  send(EventType::BigHit);           // 600 ms after start
  TEST_ASSERT_FALSE(perf->playing());
  run(0.0f, 900);                    // 1500 ms after start
  send(EventType::BigHit);
  TEST_ASSERT_EQUAL_INT(FX_BIGHIT, perf->reaction());
}

void test_lower_priority_is_dropped() {
  wakeAndSettle();
  send(EventType::BigHit);
  run(0.0f, 200);
  send(EventType::SustainStart);
  TEST_ASSERT_EQUAL_INT(FX_BIGHIT, perf->reaction());
}

void test_higher_priority_interrupts_after_guard_only() {
  wakeAndSettle();
  send(EventType::SustainStart);
  run(0.0f, 50);
  send(EventType::BigHit);
  TEST_ASSERT_EQUAL_INT(FX_SUSTAIN, perf->reaction());
  run(0.0f, 80);
  send(EventType::BigHit);
  TEST_ASSERT_EQUAL_INT(FX_BIGHIT, perf->reaction());
}

void test_repeat_flurry_extends_instead_of_restarting() {
  wakeAndSettle();
  send(EventType::Flurry);
  run(0.0f, 200);
  send(EventType::Flurry);
  run(0.0f, 250);
  TEST_ASSERT_EQUAL_INT(FX_FLURRY, perf->reaction());
  run(0.0f, 60);
  TEST_ASSERT_FALSE(perf->playing());
}

void test_until_event_reaches_performer() {
  wakeAndSettle();
  send(EventType::SustainStart);
  run(0.0f, 100);
  TEST_ASSERT_EQUAL_UINT16(8, perf->pose());
  send(EventType::SustainEnd);
  run(0.0f, 200);
  TEST_ASSERT_EQUAL_UINT16(9, perf->pose());
}

void test_drift_off_then_any_event_wakes() {
  wakeAndSettle();
  for (uint32_t i = 0; i < 15000 && brain->mood() != Mood::Asleep; i += 10) run(0.0f, 10);
  TEST_ASSERT_EQUAL_INT((int)Mood::Asleep, (int)brain->mood());
  TEST_ASSERT_EQUAL_INT(FX_DRIFTOFF, perf->reaction());
  send(EventType::Pick);
  TEST_ASSERT_EQUAL_INT(FX_WAKE, perf->reaction());
  TEST_ASSERT_EQUAL_INT((int)Mood::Curious, (int)brain->mood());
}

void test_reset_returns_to_sleep() {
  wakeAndSettle();
  brain->reset(t);
  TEST_ASSERT_EQUAL_INT((int)Mood::Asleep, (int)brain->mood());
  TEST_ASSERT_FALSE(perf->playing());
  TEST_ASSERT_EQUAL_UINT16(0, perf->pose());
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_event_while_asleep_plays_wake_only);
  RUN_TEST(test_reaction_respects_mood_filter);
  RUN_TEST(test_variants_never_repeat_back_to_back);
  RUN_TEST(test_cooldown_from_reaction_start);
  RUN_TEST(test_lower_priority_is_dropped);
  RUN_TEST(test_higher_priority_interrupts_after_guard_only);
  RUN_TEST(test_repeat_flurry_extends_instead_of_restarting);
  RUN_TEST(test_until_event_reaches_performer);
  RUN_TEST(test_drift_off_then_any_event_wakes);
  RUN_TEST(test_reset_returns_to_sleep);
  return UNITY_END();
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pio test -e native -f test_brain`
Expected: compile error, `core/brain.h: No such file or directory`.

- [ ] **Step 3: Create `src/core/brain.h`**

```cpp
#pragma once
#include <stdint.h>
#include "art_tables.h"
#include "mood.h"
#include "music_event.h"
#include "performer.h"
#include "rng.h"

// Decides what the pet does: tracks mood, maps events to reactions
// (mood filter, variants, cooldowns, priority) and drives the Performer.
class Brain {
 public:
  Brain(const ArtTables& art, Rng& rng, Performer& performer,
        const MoodConfig& moodCfg = MoodConfig());
  void  reset(uint32_t now);
  void  onEvent(const MusicEvent& e, uint32_t now);
  void  tick(const Features& f, uint32_t now);
  Mood  mood()   const { return mood_.mood(); }
  float energy() const { return mood_.energy(); }

 private:
  void fire(Trigger t, uint32_t now);
  int  pick(Trigger t, Mood m);
  bool matches(int i, Trigger t, Mood m) const;

  const ArtTables& art_;
  Rng&             rng_;
  Performer&       perf_;
  MoodModel        mood_;
  int      lastVariant_[TRIGGER_COUNT];
  bool     started_[TRIGGER_COUNT];
  uint32_t lastStart_[TRIGGER_COUNT];
  uint16_t cooldown_[TRIGGER_COUNT];
};
```

- [ ] **Step 4: Create `src/core/brain.cpp`**

```cpp
#include "brain.h"

Brain::Brain(const ArtTables& art, Rng& rng, Performer& performer, const MoodConfig& moodCfg)
    : art_(art), rng_(rng), perf_(performer), mood_(moodCfg) {
  reset(0);
}

void Brain::reset(uint32_t now) {
  mood_.reset(now);
  perf_.reset(mood_.mood(), now);
  for (int i = 0; i < TRIGGER_COUNT; i++) {
    lastVariant_[i] = -1;
    started_[i] = false;
    lastStart_[i] = 0;
    cooldown_[i] = 0;
  }
}

void Brain::onEvent(const MusicEvent& e, uint32_t now) {
  if (mood_.onEvent(e, now) == MoodChange::Woke) {  // event consumed by waking
    fire(Trigger::Wake, now);
    return;
  }
  perf_.onEvent(e.type);
  if (e.type == EventType::Pick) {
    perf_.onPick(e.strength, now);
    return;
  }
  Trigger t = triggerFor(e.type);
  if (t != Trigger::None) fire(t, now);
}

void Brain::tick(const Features& f, uint32_t now) {
  if (mood_.tick(f, now) == MoodChange::FellAsleep) fire(Trigger::DriftOff, now);
  perf_.tick(mood_.mood(), now);
}

void Brain::fire(Trigger t, uint32_t now) {
  int ti = (int)t;
  if (perf_.playing() && perf_.trigger() == t) {  // extend rule
    perf_.extend(now);
    return;
  }
  if (started_[ti] && now - lastStart_[ti] < cooldown_[ti]) return;
  if (!perf_.canInterrupt(t, now)) return;
  int r = pick(t, mood_.mood());
  if (r < 0) return;
  perf_.start(r, t, now);
  lastVariant_[ti] = r;
  started_[ti] = true;
  lastStart_[ti] = now;
  cooldown_[ti] = art_.reactions[r].cooldownMs;
}

bool Brain::matches(int i, Trigger t, Mood m) const {
  const Reaction& r = art_.reactions[i];
  return r.trigger == t && (r.moodMask == 0 || (r.moodMask & moodBit(m)));
}

// Uniform among matching reactions, excluding the last variant used for this
// trigger unless it is the only match.
int Brain::pick(Trigger t, Mood m) {
  int last = lastVariant_[(int)t];
  int fallback = -1, candidates = 0;
  for (int i = 0; i < art_.reactionCount; i++) {
    if (!matches(i, t, m)) continue;
    if (i == last) fallback = i;
    else candidates++;
  }
  if (candidates == 0) return fallback;
  uint32_t k = rng_.range(0, candidates - 1);
  for (int i = 0; i < art_.reactionCount; i++) {
    if (!matches(i, t, m) || i == last) continue;
    if (k-- == 0) return i;
  }
  return fallback;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pio test -e native -f test_brain`
Expected: `10 Tests 0 Failures`.

- [ ] **Step 6: Run the whole native suite**

Run: `pio test -e native`
Expected: all 5 suites PASSED (50 tests).

- [ ] **Step 7: Commit**

```bash
git add src/core/brain.h src/core/brain.cpp test/test_brain
git commit -m "Add Brain: mood-filtered reaction picking, cooldowns, extend rule

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Art builder and placeholder manifest

**Files:**
- Create: `tools/build_art.py`, `tools/test_build_art.py`, `art/manifest.toml`
- Generated: `src/gen/pose_meta.h`, `src/gen/pose_pixels.h`

Placeholder geometry: wizard sheets are 250×250 frames with feet at source y = 167. A 96×112 window with top-left (80, 59) in each frame puts the feet on the spec baseline (canvas y = 108) at 1:1 scale.

- [ ] **Step 1: Write the failing test** — `tools/test_build_art.py`

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import build_art as ba  # noqa: E402

POSES = {"a": 0, "b": 1}
IDLE_SHEET = "sprites/EVil Wizard 2/Sprites/Idle.png"


def reaction(**overrides):
    r = {"id": "r", "trigger": "BigHit", "steps": [{"pose": "a", "hold": 100}]}
    r.update(overrides)
    return {"reactions": [r]}


def test_basic_reaction_defaults():
    steps, reactions = ba.build_reactions(reaction(), POSES)
    assert steps == ["{0, 100, 100, Eye::Auto, EventType::None, 5000}"]
    assert reactions == [("r", "{Trigger::BigHit, 0, 1500, 0, 1}")]


def test_full_step_fields():
    m = reaction(steps=[{"pose": "@current", "hold": [100, 200], "eyes": "Wide",
                         "until": "SustainEnd", "until_max": 900}],
                 moods=["IntoIt", "Hyped"], cooldown=800)
    steps, reactions = ba.build_reactions(m, POSES)
    assert steps == ["{POSE_CURRENT, 100, 200, Eye::Wide, EventType::SustainEnd, 900}"]
    assert reactions == [("r", "{Trigger::BigHit, 12, 800, 0, 1}")]


def test_unknown_pose():
    with pytest.raises(ba.ArtError, match="unknown pose 'zzz'"):
        ba.build_reactions(reaction(steps=[{"pose": "zzz", "hold": 1}]), POSES)


@pytest.mark.parametrize("field,value,msg", [
    ("trigger", "Sneeze", "trigger"),
    ("moods", ["Grumpy"], "mood"),
    ("steps", [{"pose": "a", "hold": [300, 100]}], "hold"),
    ("steps", [{"pose": "a", "hold": 100, "eyes": "Squint"}], "eyes"),
    ("steps", [{"pose": "a", "hold": 100, "until": "Sneeze"}], "until"),
    ("steps", [], "no steps"),
])
def test_invalid_reaction_fields(field, value, msg):
    with pytest.raises(ba.ArtError, match=msg):
        ba.build_reactions(reaction(**{field: value}), POSES)


def test_idles_require_every_mood():
    m = {"idles": {"Asleep": ["a"], "Curious": ["a"], "IntoIt": ["b"]}}
    with pytest.raises(ba.ArtError, match="Hyped"):
        ba.build_idles(m, POSES)


def test_idles_flatten():
    m = {"idles": {"Asleep": ["a"], "Curious": ["a", "b"], "IntoIt": ["b"], "Hyped": ["a", "b"]}}
    flat, loops = ba.build_idles(m, POSES)
    assert flat == [0, 0, 1, 1, 0, 1]
    assert loops == ["{0, 1}", "{1, 2}", "{3, 1}", "{4, 2}"]


def test_sheet_frame_out_of_range():
    with pytest.raises(ba.ArtError, match="out of range"):
        ba.load_canvas("sprites/EVil Wizard 2/Sprites/Jump.png#5")


def test_missing_file():
    with pytest.raises(ba.ArtError, match="missing"):
        ba.load_canvas("art/poses/nope.png")


def test_pose_needs_eyes():
    with pytest.raises(ba.ArtError, match="eyes"):
        ba.process_pose("x", {"src": f"{IDLE_SHEET}#0"})


def test_sheet_pose_is_cropped_onto_baseline():
    p = ba.process_pose("x", {"src": f"{IDLE_SHEET}#0", "eyes": [52, 30]})
    assert p["x"] >= 0 and p["x"] + p["w"] <= 96
    assert p["y"] + p["h"] == 108  # feet on the baseline
    assert len(p["pixels"]) == p["w"] * p["h"]
    assert (p["ex"], p["ey"]) == (52, 30)


def test_baked_eyes():
    p = ba.process_pose("x", {"src": f"{IDLE_SHEET}#0", "eyes": "baked"})
    assert (p["ex"], p["ey"]) == (-1, -1)


def test_sheet_poses_expand():
    m = {"sheet_poses": [{"prefix": "idle", "src": IDLE_SHEET, "frames": [0, 2], "eyes": [1, 2]}]}
    poses = ba.collect_poses(m)
    assert list(poses) == ["idle_0", "idle_2"]
    assert poses["idle_2"]["src"] == f"{IDLE_SHEET}#2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pillow --with pytest pytest tools/test_build_art.py -q`
Expected: `ModuleNotFoundError: No module named 'build_art'`.

- [ ] **Step 3: Create `tools/build_art.py`**

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Build the firmware's pose / reaction / idle tables from art/manifest.toml.

Usage:  uv run tools/build_art.py

Emits:
  src/gen/pose_meta.h    plain C++ (core + tests can include it)
  src/gen/pose_pixels.h  PROGMEM RGB565 pixels (renderer only)

Pose sources are either a 96x112 PNG, or "<sheet.png>#<frame>" to slice a
placeholder Evil Wizard sheet. Frames are stored cropped to their bounding
box, with the offset inside the 96x112 canvas.
"""

import sys
import tomllib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "art" / "manifest.toml"
OUT = ROOT / "src" / "gen"

CANVAS_W, CANVAS_H = 96, 112
SHEET_FRAME = 250          # Evil Wizard sheets: 250x250 frames
SHEET_WINDOW = (80, 59)    # canvas top-left inside a frame; feet land on y=108

MOODS = ["Asleep", "Curious", "IntoIt", "Hyped"]
EYES = ["Auto", "Open", "Blink", "LookL", "LookR", "Wide", "HappyClosed"]
EVENTS = ["Pick", "BigHit", "Flurry", "SustainStart", "SustainEnd",
          "SwellStart", "SwellPeak", "Cut"]
TRIGGERS = ["DriftOff", "Sustain", "Swell", "Flurry", "Cut", "BigHit", "Wake"]
DEFAULT_COOLDOWN = 1500
DEFAULT_UNTIL_MAX = 5000
HEADER = "// Auto-generated by tools/build_art.py from art/manifest.toml — do not edit."


class ArtError(Exception):
    pass


def fail(msg):
    raise ArtError(msg)


def to_rgb565(r, g, b):
    # Swap R/B for BGR-wired ST7735 panels.
    return ((b & 0xF8) << 8) | ((g & 0xFC) << 3) | (r >> 3)


def load_canvas(src):
    """Return a 96x112 RGBA image for a pose source."""
    path, _, frame = src.partition("#")
    if not (ROOT / path).exists():
        fail(f"{src}: file missing")
    img = Image.open(ROOT / path).convert("RGBA")
    if not frame:
        if img.size != (CANVAS_W, CANVAS_H):
            fail(f"{src}: must be {CANVAS_W}x{CANVAS_H}, got {img.size[0]}x{img.size[1]}")
        return img
    frame = int(frame)
    n = img.width // SHEET_FRAME
    if not 0 <= frame < n:
        fail(f"{src}: frame {frame} out of range (sheet has {n})")
    x0 = frame * SHEET_FRAME + SHEET_WINDOW[0]
    y0 = SHEET_WINDOW[1]
    return img.crop((x0, y0, x0 + CANVAS_W, y0 + CANVAS_H))


def collect_poses(m):
    """Explicit [poses.*] plus [[sheet_poses]] expanded to <prefix>_<frame>."""
    poses = {}
    for sp in m.get("sheet_poses", []):
        for f in sp["frames"]:
            poses[f"{sp['prefix']}_{f}"] = {"src": f"{sp['src']}#{f}", "eyes": sp.get("eyes")}
    for name, p in m.get("poses", {}).items():
        if name in poses:
            fail(f"duplicate pose {name!r}")
        poses[name] = p
    return poses


def process_pose(name, p):
    eyes = p.get("eyes")
    if eyes == "baked":
        ex, ey = -1, -1
    elif isinstance(eyes, list) and len(eyes) == 2:
        ex, ey = eyes
    else:
        fail(f"pose {name}: needs eyes = [x, y] or \"baked\"")
    img = load_canvas(p["src"])
    box = img.getchannel("A").getbbox()
    if not box:
        fail(f"pose {name}: image is empty")
    flat = Image.new("RGB", img.size, (0, 0, 0))
    flat.paste(img, mask=img.getchannel("A"))
    x0, y0, x1, y1 = box
    pixels = [to_rgb565(*px) for px in flat.crop(box).getdata()]
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0, "ex": ex, "ey": ey, "pixels": pixels}


def parse_hold(h, where):
    if isinstance(h, int):
        return h, h
    if isinstance(h, list) and len(h) == 2 and h[0] <= h[1]:
        return h[0], h[1]
    fail(f"{where}: hold must be ms or [min, max] with min <= max")


def build_reactions(m, pose_index):
    """Return (step initialisers, [(id, reaction initialiser)])."""
    steps, reactions = [], []
    for r in m.get("reactions", []):
        rid = r.get("id") or fail("reaction without id")
        trig = r.get("trigger")
        if trig not in TRIGGERS:
            fail(f"reaction {rid}: unknown trigger {trig!r}")
        mask = 0
        for mood in r.get("moods", []):
            if mood not in MOODS:
                fail(f"reaction {rid}: unknown mood {mood!r}")
            mask |= 1 << MOODS.index(mood)
        if not r.get("steps"):
            fail(f"reaction {rid}: no steps")
        first = len(steps)
        for i, s in enumerate(r["steps"]):
            where = f"reaction {rid} step {i}"
            pose = s.get("pose")
            if pose == "@current":
                pid = "POSE_CURRENT"
            elif pose in pose_index:
                pid = str(pose_index[pose])
            else:
                fail(f"{where}: unknown pose {pose!r}")
            hmin, hmax = parse_hold(s.get("hold"), where)
            eyes = s.get("eyes", "Auto")
            if eyes not in EYES:
                fail(f"{where}: unknown eyes {eyes!r}")
            until = s.get("until", "None")
            if until != "None" and until not in EVENTS:
                fail(f"{where}: unknown until event {until!r}")
            until_max = s.get("until_max", DEFAULT_UNTIL_MAX)
            steps.append(f"{{{pid}, {hmin}, {hmax}, Eye::{eyes}, EventType::{until}, {until_max}}}")
        cooldown = r.get("cooldown", DEFAULT_COOLDOWN)
        reactions.append((rid, f"{{Trigger::{trig}, {mask}, {cooldown}, {first}, {len(r['steps'])}}}"))
    return steps, reactions


def build_idles(m, pose_index):
    """Return (flat pose index list, IdleLoop initialisers in Mood order)."""
    idles = m.get("idles", {})
    flat, loops = [], []
    for mood in MOODS:
        names = idles.get(mood) or fail(f"idles.{mood}: needs at least one pose")
        loops.append(f"{{{len(flat)}, {len(names)}}}")
        for n in names:
            if n not in pose_index:
                fail(f"idles.{mood}: unknown pose {n!r}")
            flat.append(pose_index[n])
    return flat, loops


def emit_meta(poses, steps, reactions, idle_flat, idle_loops):
    out = [HEADER, "#pragma once", '#include "../core/art_tables.h"', "", "namespace gen {", ""]
    out.append("static const PoseMeta POSES[] = {")
    for name, p in poses:
        out.append(f"  {{{p['x']}, {p['y']}, {p['w']}, {p['h']}, {p['ex']}, {p['ey']}}},  // {name}")
    out += ["};", "", "static const Step STEPS[] = {"]
    out += [f"  {s}," for s in steps]
    out += ["};", "", "static const Reaction REACTIONS[] = {"]
    out += [f"  {r},  // {rid}" for rid, r in reactions]
    out += ["};", ""]
    out.append("static const char* const REACTION_IDS[] = {"
               + ", ".join(f'"{rid}"' for rid, _ in reactions) + "};")
    out.append("static const uint16_t IDLE_POSES[] = {" + ", ".join(map(str, idle_flat)) + "};")
    out += ["", "static const ArtTables ART = {",
            f"  POSES, {len(poses)},",
            f"  STEPS, {len(steps)},",
            f"  REACTIONS, {len(reactions)},",
            "  IDLE_POSES,",
            "  {" + ", ".join(idle_loops) + "},",
            "};", "", "}  // namespace gen", ""]
    return "\n".join(out)


def emit_pixels(poses):
    out = [HEADER, "#pragma once", "#include <Arduino.h>", "", "namespace gen {", ""]
    for i, (name, p) in enumerate(poses):
        px = p["pixels"]
        out.append(f"static const uint16_t PIX_{i}[{len(px)}] PROGMEM = {{  // {name}")
        for j in range(0, len(px), 16):
            out.append("  " + ", ".join(f"0x{v:04X}" for v in px[j:j + 16]) + ",")
        out += ["};", ""]
    out.append("static const uint16_t* const POSE_PIXELS[] = {"
               + ", ".join(f"PIX_{i}" for i in range(len(poses))) + "};")
    out += ["", "}  // namespace gen", ""]
    return "\n".join(out)


def main():
    try:
        m = tomllib.loads(MANIFEST.read_text())
        raw = collect_poses(m)
        index = {name: i for i, name in enumerate(raw)}
        poses = [(name, process_pose(name, p)) for name, p in raw.items()]
        steps, reactions = build_reactions(m, index)
        if not reactions:
            fail("manifest has no reactions")
        idle_flat, idle_loops = build_idles(m, index)
    except ArtError as e:
        print(f"build_art: {e}", file=sys.stderr)
        sys.exit(1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pose_meta.h").write_text(emit_meta(poses, steps, reactions, idle_flat, idle_loops))
    (OUT / "pose_pixels.h").write_text(emit_pixels(poses))
    total = sum(len(p["pixels"]) * 2 for _, p in poses)
    print(f"build_art: {len(poses)} poses ({total / 1024:.0f} KB pixels), "
          f"{len(reactions)} reactions, {len(steps)} steps")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pillow --with pytest pytest tools/test_build_art.py -q`
Expected: `17 passed`.

- [ ] **Step 5: Create `art/manifest.toml`**

```toml
# Placeholder art: Evil Wizard sheet frames standing in for the real pet
# until the Blender pack (sub-project 2). [[sheet_poses]] expands to poses
# named <prefix>_<frame>. Eye anchors are rough guesses — the overlay only
# exists to exercise the mechanism.

[[sheet_poses]]
prefix = "idle"
src    = "sprites/EVil Wizard 2/Sprites/Idle.png"
frames = [0, 1, 2, 3, 4, 6]
eyes   = [52, 30]

[[sheet_poses]]
prefix = "run"
src    = "sprites/EVil Wizard 2/Sprites/Run.png"
frames = [0, 2, 4, 6]
eyes   = [52, 36]

[[sheet_poses]]
prefix = "attack1"
src    = "sprites/EVil Wizard 2/Sprites/Attack1.png"
frames = [0, 3, 6, 7]
eyes   = [40, 36]

[[sheet_poses]]
prefix = "attack2"
src    = "sprites/EVil Wizard 2/Sprites/Attack2.png"
frames = [0, 1, 2, 3, 4, 5, 6, 7]
eyes   = [52, 30]

[[sheet_poses]]
prefix = "hit"
src    = "sprites/EVil Wizard 2/Sprites/Take hit.png"
frames = [0, 1, 2]
eyes   = [52, 30]

[[sheet_poses]]
prefix = "jump"
src    = "sprites/EVil Wizard 2/Sprites/Jump.png"
frames = [0, 1]
eyes   = [48, 34]

[[sheet_poses]]
prefix = "fall"
src    = "sprites/EVil Wizard 2/Sprites/Fall.png"
frames = [0, 1]
eyes   = [52, 30]

[[sheet_poses]]
prefix = "death"
src    = "sprites/EVil Wizard 2/Sprites/Death.png"
frames = [2, 4, 5, 6]
eyes   = "baked"

[idles]
Asleep  = ["death_5", "death_6"]
Curious = ["idle_0", "idle_2", "idle_4"]
IntoIt  = ["run_0", "run_2", "run_4", "run_6"]
Hyped   = ["attack1_0", "attack1_3", "attack1_6"]

[[reactions]]
id      = "big_hit_a"
trigger = "BigHit"
steps = [
  { pose = "hit_0", hold = 80,         eyes = "Wide" },
  { pose = "hit_1", hold = [350, 500], eyes = "Wide" },
  { pose = "hit_2", hold = 250 },
]

[[reactions]]
id      = "big_hit_b"
trigger = "BigHit"
moods   = ["Hyped"]
steps = [
  { pose = "fall_0",    hold = 80,         eyes = "Wide" },
  { pose = "fall_1",    hold = [400, 600], eyes = "Wide" },
  { pose = "attack1_7", hold = 250 },
]

[[reactions]]
id      = "flurry_a"
trigger = "Flurry"
steps = [
  { pose = "attack2_0", hold = [70, 90] },
  { pose = "attack2_1", hold = [70, 90] },
  { pose = "attack2_2", hold = [70, 90] },
  { pose = "attack2_3", hold = [70, 90] },
  { pose = "attack2_4", hold = [70, 90] },
  { pose = "attack2_5", hold = [70, 90] },
  { pose = "attack2_6", hold = [70, 90] },
  { pose = "attack2_7", hold = [120, 160] },
]

[[reactions]]
id      = "swell_a"
trigger = "Swell"
steps = [
  { pose = "idle_6", hold = 200 },
  { pose = "jump_0", hold = 300, until = "SwellPeak", until_max = 5000 },
  { pose = "jump_1", hold = 400, eyes = "Wide" },
  { pose = "fall_1", hold = 200 },
]

[[reactions]]
id      = "sustain_a"
trigger = "Sustain"
steps = [
  { pose = "idle_1", hold = 200, eyes = "Wide" },
  { pose = "jump_0", hold = 400, eyes = "Wide", until = "SustainEnd", until_max = 6000 },
  { pose = "idle_0", hold = 300, eyes = "HappyClosed" },
]

[[reactions]]
id      = "cut_a"
trigger = "Cut"
steps = [
  { pose = "@current",  hold = 600 },
  { pose = "attack1_7", hold = 700, eyes = "Wide" },
]

[[reactions]]
id      = "wake_a"
trigger = "Wake"
steps = [
  { pose = "hit_0",  hold = 120, eyes = "Wide" },
  { pose = "idle_0", hold = 400, eyes = "LookL" },
  { pose = "idle_0", hold = 400, eyes = "LookR" },
  { pose = "idle_0", hold = 300 },
]

[[reactions]]
id      = "drift_off_a"
trigger = "DriftOff"
steps = [
  { pose = "idle_3",  hold = 600, eyes = "HappyClosed" },
  { pose = "death_2", hold = 400 },
  { pose = "death_4", hold = 400 },
  { pose = "death_6", hold = 500 },
]
```

- [ ] **Step 6: Generate the headers**

Run: `uv run tools/build_art.py`
Expected: `build_art: 33 poses (... KB pixels), 8 reactions, 31 steps` with the pixel total well under 600 KB.

- [ ] **Step 7: Sanity-check the generated meta compiles as plain C++**

Run: `mkdir -p .pio/check && printf '#include "gen/pose_meta.h"\nint main(){return gen::ART.poseCount==33?0:1;}\n' > .pio/check/meta.cpp && c++ -std=c++17 -I src .pio/check/meta.cpp -o .pio/check/meta && .pio/check/meta && echo OK`
Expected: `OK`.

- [ ] **Step 8: Commit**

```bash
git add tools/build_art.py tools/test_build_art.py art/manifest.toml src/gen
git commit -m "Add manifest-driven art builder and placeholder wizard manifest

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Platform layer — mock input, renderer, main

**Files:**
- Create: `src/platform/mock_input.h`, `src/platform/mock_input.cpp`, `src/platform/scripts.h`, `src/platform/renderer_tft.h`, `src/platform/renderer_tft.cpp`, `src/platform/live_audio.h`, `src/platform/live_audio.cpp`, `src/platform/main.cpp`
- Delete: `src/main.cpp`, `src/sprites/`, `tools/convert_sprites.py`

No unit tests here (hardware I/O); verified by build in this task and on the device in Task 9.

- [ ] **Step 1: Create `src/platform/scripts.h`**

```cpp
#pragma once
#include <stdint.h>

// A scripted timeline is a list of mock key presses. Each entry fires `key`
// `repeat` times, starting at t_ms and spaced every_ms apart. Entries run
// independently, so they may overlap.
struct ScriptEntry { uint32_t t_ms; char key; uint16_t repeat; uint16_t every_ms; };
struct Script      { const ScriptEntry* entries; uint8_t count; };

// 1: a ~60 s "set". Ends in silence; the pet then winds down to sleep
// (Hyped → IntoIt → Curious → Asleep takes ~20 s more).
static const ScriptEntry SCRIPT_SET[] = {
  {    0, '0',  1,    0 },  // silence
  { 3000, 'p',  1,    0 },  // first note wakes it
  { 4000, '+',  2,    0 },  // level 0.2
  { 4000, 'p', 20,  500 },  // noodling
  {14000, '+',  3, 1000 },  // build to 0.5
  {14000, 'P', 24,  250 },  // dig in: beat-step idle
  {20000, '+',  4,  500 },  // up to 0.9 → Hyped
  {20000, 'f',  4,  600 },  // flurry (repeats extend it)
  {24000, 'h',  1,    0 },  // big hit
  {25000, 'P', 16,  250 },  // keep playing
  {29500, 'c',  1,    0 },  // cut
  {31000, 's',  1,    0 },  // sustain...
  {35000, 'S',  1,    0 },  // ...released
  {36000, 'w',  1,    0 },  // swell
  {36000, '+',  5,  600 },
  {39000, 'W',  1,    0 },  // swell peak
  {39500, '-',  6, 1000 },  // fade out
  {39500, 'p', 10,  800 },
  {48000, '0',  1,    0 },  // silence
};

// 2: priority drill — hit, cut, flurry, hit-during-flurry.
static const ScriptEntry SCRIPT_PRIORITY[] = {
  {    0, 'p', 1,    0 },
  {    0, '+', 6,    0 },
  { 2000, 'h', 1,    0 },
  { 5000, 'c', 1,    0 },
  { 6000, '+', 6,    0 },
  { 8000, 'f', 3,  500 },
  { 8800, 'h', 1,    0 },
  {12000, 'c', 1,    0 },
};

// 3: hold drill — short sustain, long sustain, swell without peak.
static const ScriptEntry SCRIPT_HOLDS[] = {
  {    0, 'p', 1, 0 },
  { 2000, 's', 1, 0 },
  { 2300, 'S', 1, 0 },
  { 5000, 's', 1, 0 },
  { 9000, 'S', 1, 0 },
  {12000, 'w', 1, 0 },  // no peak: crouch caps at 5 s, then leaps anyway
};

#define SCRIPT_LEN(a) (uint8_t)(sizeof(a) / sizeof(a[0]))
static const Script SCRIPTS[] = {
  {SCRIPT_SET,      SCRIPT_LEN(SCRIPT_SET)},
  {SCRIPT_PRIORITY, SCRIPT_LEN(SCRIPT_PRIORITY)},
  {SCRIPT_HOLDS,    SCRIPT_LEN(SCRIPT_HOLDS)},
};
constexpr int SCRIPT_COUNT = 3;
```

- [ ] **Step 2: Create `src/platform/mock_input.h`**

```cpp
#pragma once
#include <stdint.h>
#include "core/music_event.h"
#include "scripts.h"

// Keyboard / scripted stand-in for the live audio detectors.
// Keys: p P h f s S w W c + - 0 1-3 d r (see key()).
class MockInput {
 public:
  void     reset();
  void     key(char c, uint32_t now);
  void     tick(uint32_t now);                      // advances a running script
  bool     pop(uint32_t now, MusicEvent& out);      // next due event, in order
  Features features(uint32_t now) const;
  bool     takeHudToggle() { bool r = hud_; hud_ = false; return r; }
  bool     takeReset()     { bool r = reset_; reset_ = false; return r; }

 private:
  void  schedule(EventType type, float strength, uint32_t at);
  void  runScript(int n, uint32_t now);
  void  lift(float level, uint32_t now);
  float liftNow(uint32_t now) const;

  static constexpr int      QUEUE  = 32;
  static constexpr int      MAX_SCRIPT = 32;
  static constexpr uint32_t LIFT_MS = 300;

  MusicEvent queue_[QUEUE];
  int        count_ = 0;
  float      base_ = 0, lift_ = 0;
  uint32_t   liftAt_ = 0;
  const Script* script_ = nullptr;
  uint32_t   scriptStart_ = 0;
  uint16_t   fired_[MAX_SCRIPT] = {};
  bool       hud_ = false, reset_ = false;
};
```

- [ ] **Step 3: Create `src/platform/mock_input.cpp`**

```cpp
#include "mock_input.h"
#include <math.h>

void MockInput::reset() {
  count_ = 0;
  base_ = lift_ = 0;
  script_ = nullptr;
}

void MockInput::key(char c, uint32_t now) {
  switch (c) {
    case 'p': schedule(EventType::Pick, 0.4f, now); break;
    case 'P': schedule(EventType::Pick, 0.9f, now); break;
    case 'h': schedule(EventType::BigHit, 1.0f, now); lift(1.0f, now); break;
    case 'f':
      for (int i = 0; i < 8; i++) schedule(EventType::Pick, 0.7f, now + i * 80);
      schedule(EventType::Flurry, 1.0f, now + 160);
      break;
    case 's': schedule(EventType::SustainStart, 1.0f, now); base_ = fmaxf(base_, 0.5f); break;
    case 'S': schedule(EventType::SustainEnd, 1.0f, now); base_ = 0.1f; break;
    case 'w': schedule(EventType::SwellStart, 1.0f, now); break;
    case 'W': schedule(EventType::SwellPeak, 1.0f, now); lift(1.0f, now); break;
    case 'c': schedule(EventType::Cut, 1.0f, now); base_ = 0; lift_ = 0; break;
    case '+': base_ = fminf(1.0f, base_ + 0.1f); break;
    case '-': base_ = fmaxf(0.0f, base_ - 0.1f); break;
    case '0': base_ = 0; lift_ = 0; break;
    case '1': case '2': case '3': runScript(c - '1', now); break;
    case 'd': hud_ = true; break;
    case 'r': reset_ = true; break;
    default: break;  // includes \r and \n from the serial monitor
  }
}

void MockInput::schedule(EventType type, float strength, uint32_t at) {
  if (count_ < QUEUE) queue_[count_++] = {type, at, strength};
}

void MockInput::runScript(int n, uint32_t now) {
  if (n < 0 || n >= SCRIPT_COUNT || SCRIPTS[n].count > MAX_SCRIPT) return;
  script_ = &SCRIPTS[n];
  scriptStart_ = now;
  for (int i = 0; i < MAX_SCRIPT; i++) fired_[i] = 0;
}

void MockInput::tick(uint32_t now) {
  if (!script_) return;
  bool done = true;
  for (int i = 0; i < script_->count; i++) {
    const ScriptEntry& e = script_->entries[i];
    while (fired_[i] < e.repeat && now - scriptStart_ >= e.t_ms + fired_[i] * (uint32_t)e.every_ms) {
      fired_[i]++;
      key(e.key, now);
    }
    if (fired_[i] < e.repeat) done = false;
  }
  if (done) script_ = nullptr;
}

bool MockInput::pop(uint32_t now, MusicEvent& out) {
  int best = -1;
  for (int i = 0; i < count_; i++) {
    if ((int32_t)(now - queue_[i].t_ms) < 0) continue;
    if (best < 0 || (int32_t)(queue_[i].t_ms - queue_[best].t_ms) < 0) best = i;
  }
  if (best < 0) return false;
  out = queue_[best];
  for (int i = best; i < count_ - 1; i++) queue_[i] = queue_[i + 1];  // keep arrival order
  count_--;
  if (out.type == EventType::Pick) lift(out.strength, now);
  return true;
}

void MockInput::lift(float level, uint32_t now) {
  lift_ = fmaxf(liftNow(now), level);
  liftAt_ = now;
}

float MockInput::liftNow(uint32_t now) const {
  float k = 1.0f - (float)(now - liftAt_) / LIFT_MS;
  return k > 0 ? lift_ * k : 0.0f;
}

Features MockInput::features(uint32_t now) const {
  return {fmaxf(base_, liftNow(now)), 0.0f};
}
```

- [ ] **Step 4: Create `src/platform/renderer_tft.h`**

```cpp
#pragma once
#include <TFT_eSPI.h>
#include "core/art_tables.h"

struct HudInfo {
  const char* mood;
  float       energy;
  const char* reaction;  // nullptr when idle
  int         step;
};

class RendererTft {
 public:
  void begin();
  void draw(uint16_t pose, Eye eye, const HudInfo* hud);  // hud == nullptr hides it

 private:
  void drawEyes(int cx, int cy, Eye eye);

  TFT_eSPI    tft_;
  TFT_eSprite canvas_{&tft_};
};
```

- [ ] **Step 5: Create `src/platform/renderer_tft.cpp`**

```cpp
#include "renderer_tft.h"
#include "gen/pose_meta.h"
#include "gen/pose_pixels.h"

namespace {
constexpr int16_t  SCREEN_W = 160;
constexpr int16_t  SCREEN_H = 128;
constexpr int16_t  CANVAS_X = (SCREEN_W - 96) / 2;  // 96x112 pose canvas
constexpr int16_t  CANVAS_Y = SCREEN_H - 112 - 4;
// Black until the real art arrives with its off-white + sun background (sub-project 2).
constexpr uint16_t BG  = TFT_BLACK;
constexpr uint16_t EYE = TFT_WHITE;
}  // namespace

void RendererTft::begin() {
  tft_.init();
  tft_.setRotation(1);
  tft_.fillScreen(BG);
  canvas_.setColorDepth(16);
  canvas_.createSprite(SCREEN_W, SCREEN_H);
  canvas_.setSwapBytes(true);
}

void RendererTft::draw(uint16_t pose, Eye eye, const HudInfo* hud) {
  canvas_.fillSprite(BG);
  const PoseMeta& m = gen::POSES[pose];
  canvas_.pushImage(CANVAS_X + m.x, CANVAS_Y + m.y, m.w, m.h, (uint16_t*)gen::POSE_PIXELS[pose]);
  if (m.eyeX != EYES_BAKED) drawEyes(CANVAS_X + m.eyeX, CANVAS_Y + m.eyeY, eye);
  if (hud) {
    canvas_.setTextFont(1);
    canvas_.setTextColor(TFT_WHITE, BG);
    canvas_.setCursor(2, 2);
    canvas_.printf("%s %.2f", hud->mood, hud->energy);
    if (hud->reaction) {
      canvas_.setCursor(2, 12);
      canvas_.printf("%s #%d", hud->reaction, hud->step);
    }
  }
  canvas_.pushSprite(0, 0);
}

// Placeholder primitives: two dots 8 px apart. Real eye sprites arrive in sub-project 2.
void RendererTft::drawEyes(int cx, int cy, Eye eye) {
  int dx = eye == Eye::LookL ? -2 : eye == Eye::LookR ? 2 : 0;
  for (int side = -1; side <= 1; side += 2) {
    int x = cx + side * 4 + dx;
    switch (eye) {
      case Eye::Blink:
        canvas_.drawFastHLine(x - 1, cy, 3, EYE);
        break;
      case Eye::HappyClosed:
        canvas_.drawLine(x - 1, cy, x, cy - 1, EYE);
        canvas_.drawLine(x, cy - 1, x + 1, cy, EYE);
        break;
      case Eye::Wide:
        canvas_.fillRect(x - 2, cy - 2, 4, 4, EYE);
        break;
      default:
        canvas_.fillRect(x - 1, cy - 1, 3, 3, EYE);
        break;
    }
  }
}
```

- [ ] **Step 6: Create `src/platform/live_audio.h`**

```cpp
#pragma once
#include <stdint.h>

// ADC sampling + windowed RMS from the Phase 1 prototype. Retained for
// sub-project 3 (live signal detection); not wired into the brain yet.
class LiveAudio {
 public:
  void  begin();
  void  poll();               // call often; samples at 8 kHz
  float rms() const { return rms_; }

 private:
  uint32_t nextSampleUs_ = 0;
  uint64_t sumSquares_   = 0;
  uint32_t count_        = 0;
  float    dc_           = 2048.0f;
  float    rms_          = 0.0f;
};
```

- [ ] **Step 7: Create `src/platform/live_audio.cpp`** (logic moved verbatim from the old `src/main.cpp`)

```cpp
#include "live_audio.h"
#include <Arduino.h>

namespace {
constexpr int      AUDIO_PIN      = 34;
constexpr int      SAMPLE_HZ      = 8000;
constexpr int      WINDOW_MS      = 50;
constexpr int      WINDOW_SAMPLES = SAMPLE_HZ * WINDOW_MS / 1000;
constexpr uint32_t SAMPLE_US      = 1000000UL / SAMPLE_HZ;
}  // namespace

void LiveAudio::begin() {
  analogReadResolution(12);
  analogSetPinAttenuation(AUDIO_PIN, ADC_11db);
  nextSampleUs_ = micros();
}

void LiveAudio::poll() {
  if ((int32_t)(micros() - nextSampleUs_) < 0) return;
  nextSampleUs_ += SAMPLE_US;
  int raw = analogRead(AUDIO_PIN);
  dc_ += (raw - dc_) * 0.0005f;
  float ac = raw - dc_;
  sumSquares_ += (uint32_t)(ac * ac);
  if (++count_ >= WINDOW_SAMPLES) {
    rms_ = sqrtf((float)sumSquares_ / count_);
    sumSquares_ = 0;
    count_ = 0;
  }
}
```

- [ ] **Step 8: Create `src/platform/main.cpp`**

```cpp
#include <Arduino.h>
#include <esp_system.h>
#include "core/brain.h"
#include "core/eyes.h"
#include "core/performer.h"
#include "gen/pose_meta.h"
#include "platform/mock_input.h"
#include "platform/renderer_tft.h"

namespace {
constexpr uint32_t TICK_MS  = 10;  // input, mood, performer, eyes at 100 Hz
constexpr uint32_t FRAME_MS = 33;  // render at ~30 fps

const char* const MOOD_NAMES[] = {"Asleep", "Curious", "IntoIt", "Hyped"};

Rng           rng(1);
Performer     performer(gen::ART, rng);
Brain         brain(gen::ART, rng, performer);
EyeController eyes(rng);
MockInput     mock;
RendererTft   renderer;
bool          hud = false;
uint32_t      lastTick = 0, lastFrame = 0;

void resetAll(uint32_t now) {
  mock.reset();
  brain.reset(now);
  eyes.reset(now);
}
}  // namespace

void setup() {
  Serial.begin(115200);
  rng = Rng(esp_random());
  renderer.begin();
  resetAll(millis());
  Serial.println("PedalPets ready. Keys: p P h f s S w W c + - 0 | 1-3 scripts | d HUD | r reset");
}

void loop() {
  uint32_t now = millis();
  while (Serial.available()) mock.key((char)Serial.read(), now);
  if (mock.takeReset()) resetAll(now);
  if (mock.takeHudToggle()) hud = !hud;

  if (now - lastTick >= TICK_MS) {
    lastTick = now;
    mock.tick(now);
    MusicEvent e;
    while (mock.pop(now, e)) brain.onEvent(e, now);
    brain.tick(mock.features(now), now);
    eyes.tick(brain.mood(), performer.eyes(), now);
  }

  if (now - lastFrame >= FRAME_MS) {
    lastFrame = now;
    HudInfo info = {
      MOOD_NAMES[(int)brain.mood()],
      brain.energy(),
      performer.playing() ? gen::REACTION_IDS[performer.reaction()] : nullptr,
      performer.step(),
    };
    renderer.draw(performer.pose(), eyes.eye(), hud ? &info : nullptr);
  }
}
```

- [ ] **Step 9: Delete superseded files**

```bash
git rm -r src/main.cpp src/sprites tools/convert_sprites.py
```

- [ ] **Step 10: Build the firmware**

Run: `pio run -e esp32dev`
Expected: `SUCCESS`, with a `Flash:` usage line under 100% of the 3 MB `huge_app` partition (expect roughly 25–35%).
If the build reports `esp_random` undeclared, add `#include <esp_random.h>` to `src/platform/main.cpp`.

- [ ] **Step 11: Confirm native tests are unaffected**

Run: `pio test -e native`
Expected: all suites PASSED.

- [ ] **Step 12: Commit**

```bash
git add src/platform
git commit -m "Wire platform layer: mock input, scripts, TFT renderer, new main

Removes the RMS threshold state machine and old sprite headers.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: On-device verification (needs the board plugged in)

**Files:** none (fix-ups only if something fails).

- [ ] **Step 1: Flash**

Run: `pio run -e esp32dev -t upload`
Expected: `SUCCESS`.

- [ ] **Step 2: Open the serial monitor**

Run (user, interactive): `pio device monitor`
Expected: `PedalPets ready. Keys: ...`. Screen shows the wizard lying down (Asleep idle).

- [ ] **Step 3: Manual key checks** — press `d` (HUD on), then:

| Keys | Expect on screen |
|---|---|
| `p` | Wake: jolt, looks left, right; HUD `Curious`, reaction `wake_a` |
| `h` | `big_hit_a` within one frame; eyes wide |
| `s` … wait 3 s … `S` | `sustain_a` holds the leaning pose until `S` |
| `w` then `W` | crouch holds until `W`, then leap |
| `+` ×6, then `P` repeatedly | HUD energy climbs → `IntoIt` → `Hyped`; idle steps with each hard pick |
| `f` | `flurry_a`; press `f` again mid-flurry and it continues rather than restarting |
| `c` | freezes current pose, then points |
| `0`, wait ~20–30 s | winds down through moods, `drift_off_a`, then asleep |
| `r` | back to asleep |

- [ ] **Step 4: Run scripts** — `1` (full set, ~60 s plus wind-down), `2` (priority drill), `3` (hold drill). Watch HUD and pet stay in sync; no flicker, no stuck reactions.

- [ ] **Step 5: Record results** — note anything that felt wrong (timing, priorities) for tuning. If any check fails, use superpowers:systematic-debugging before changing code.

- [ ] **Step 6: Commit any fixes** with a message describing the fix and the trailer:

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```
