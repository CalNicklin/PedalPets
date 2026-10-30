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
  uint32_t silenceMs   = 30000;   // Curious → Asleep (time to miss you, then get bored)
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
