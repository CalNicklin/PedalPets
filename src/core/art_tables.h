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
