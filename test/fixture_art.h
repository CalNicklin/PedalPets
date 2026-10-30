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
  {{0, 1, 900}, {1, 2, 210}, {3, 2, 90}, {5, 2, 90}},
};
