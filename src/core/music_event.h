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
