#pragma once
#include "core/art_tables.h"

// Poses 0..9; geometry is irrelevant to core logic.
// Idles: Asleep {0}, Curious {1,2} @210 ms, IntoIt {3,4} @90 ms, Hyped {5,6} @90 ms.
// Holds are whole 30 ms frames except Swell, which tests quantisation.
static const PoseMeta FX_POSES[10] = {};

static const Step FX_STEPS[] = {
  // 0-1: BigHit (any mood) — 480 ms total
  {7,  90,  90, Eye::Wide, EventType::None, 0},
  {8, 390, 390, Eye::Auto, EventType::None, 0},
  // 2: BigHit (Hyped only)
  {9,  90,  90, Eye::Auto, EventType::None, 0},
  // 3-5: Sustain — middle step waits for SustainEnd (cap 1000 ms)
  {7,  90,  90, Eye::Auto, EventType::None, 0},
  {8, 210, 210, Eye::Auto, EventType::SustainEnd, 1000},
  {9,  90,  90, Eye::Auto, EventType::None, 0},
  // 6-7: Cut — freezes the current pose first
  {POSE_CURRENT, 300, 300, Eye::Auto, EventType::None, 0},
  {9, 210, 210, Eye::Auto, EventType::None, 0},
  // 8: Flurry
  {7, 300, 300, Eye::Auto, EventType::None, 0},
  // 9: Wake
  {7, 510, 510, Eye::Wide, EventType::None, 0},
  // 10: DriftOff
  {8, 510, 510, Eye::Auto, EventType::None, 0},
  // 11: Swell — random hold
  {7, 100, 300, Eye::Auto, EventType::None, 0},
  // 12-15: Loopy — steps 13-14 form a loop section
  {1, 90, 90, Eye::Auto, EventType::None, 0},
  {2, 90, 90, Eye::Auto, EventType::None, 0},
  {3, 90, 90, Eye::Auto, EventType::None, 0},
  {4, 90, 90, Eye::Auto, EventType::None, 0},
};

enum FxReaction { FX_BIGHIT, FX_BIGHIT_HYPED, FX_SUSTAIN, FX_CUT, FX_FLURRY, FX_WAKE, FX_DRIFTOFF, FX_SWELL,
                  FX_LOOP_EXTEND, FX_LOOP_UNTIL, FX_ENTRY };

// Matched entry for FX_ENTRY: from pose 4 start at step 2, else step 0.
static const uint8_t FX_ENTRY_TABLE[10] = {0, 0, 0, 0, 2, 0, 0, 0, 0, 0};

static const Reaction FX_REACTIONS[] = {
  // trigger, moods, cooldown, firstStep, stepCount, loopFrom, loopLen, loopUntil, loopMaxMs
  {Trigger::BigHit,   0,                    1500, 0,  2, 0, 0, EventType::None, 0},
  {Trigger::BigHit,   moodBit(Mood::Hyped), 1500, 2,  1, 0, 0, EventType::None, 0},
  {Trigger::Sustain,  0,                    1500, 3,  3, 0, 0, EventType::None, 0},
  {Trigger::Cut,      0,                    1500, 6,  2, 0, 0, EventType::None, 0},
  {Trigger::Flurry,   0,                    1500, 8,  1, 0, 0, EventType::None, 0},
  {Trigger::Wake,     0,                    1500, 9,  1, 0, 0, EventType::None, 0},
  {Trigger::DriftOff, 0,                    1500, 10, 1, 0, 0, EventType::None, 0},
  {Trigger::Swell,    0,                    1500, 11, 1, 0, 0, EventType::None, 0},
  // Loop fixtures are IntoIt-only so the Brain tests (Curious/Hyped) never pick them.
  {Trigger::Flurry,   moodBit(Mood::IntoIt), 1500, 12, 4, 1, 2, EventType::None, 0},
  {Trigger::Sustain,  moodBit(Mood::IntoIt), 1500, 12, 4, 1, 2, EventType::SustainEnd, 1000},
  {Trigger::Swell,    moodBit(Mood::IntoIt), 1500, 12, 4, 0, 0, EventType::None, 0, FX_ENTRY_TABLE},
};

static const uint16_t FX_IDLE_POSES[] = {0, 1, 2, 3, 4, 5, 6};


static const ArtTables FX_ART = {
  FX_POSES, 10,
  FX_STEPS, sizeof(FX_STEPS) / sizeof(FX_STEPS[0]),
  FX_REACTIONS, sizeof(FX_REACTIONS) / sizeof(FX_REACTIONS[0]),
  FX_IDLE_POSES,
  {{0, 1, 900}, {1, 2, 210}, {3, 2, 90}, {5, 2, 90}},
};
