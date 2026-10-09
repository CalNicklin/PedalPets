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
