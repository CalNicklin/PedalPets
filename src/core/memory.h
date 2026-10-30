#pragma once
#include <stdint.h>
#include "mood.h"
#include "music_event.h"

// The pet's memory of you, kept across power-offs (the platform saves it):
// how many times you've played together, for how long, how much of it was
// wild. Familiarity grows with time played together and shapes how it greets
// you and how much it misses you.

constexpr uint16_t PLAYER_MEMORY_VERSION = 1;

struct PlayerMemory {
  uint16_t version = PLAYER_MEMORY_VERSION;
  uint32_t sessions = 0;       // times it woke up to you playing
  uint32_t playSeconds = 0;    // seconds with you playing
  uint32_t hypedSeconds = 0;   // ... of which it was hyped
};

struct BondConfig {
  float    friendSeconds = 1800;   // familiarity 1 - e^-(play / this): ~0.5 after 20 min, ~0.9 after an hour
  uint32_t playingMs     = 2000;   // a note this recent means you're playing
  uint32_t saveEverySec  = 60;     // new play worth saving
};

class Bond {
 public:
  explicit Bond(const BondConfig& cfg = BondConfig()) : cfg_(cfg) {}

  void load(const PlayerMemory& m);           // an unknown version starts afresh
  void onWake(uint32_t now);                  // a new session
  void onEvent(const MusicEvent& e, uint32_t now);
  void tick(Mood mood, uint32_t now);         // every logic tick

  float               familiarity() const;   // 0 a stranger .. 1 an old friend
  const PlayerMemory& memory() const { return mem_; }
  bool                wantsSave(uint32_t now) const;
  void                saved(uint32_t now);

 private:
  BondConfig   cfg_;
  PlayerMemory mem_;
  uint32_t     lastNote_ = 0, lastTick_ = 0, msPlay_ = 0, msHyped_ = 0;
  bool         heard_ = false, sessionUnsaved_ = false;
  uint32_t     playAtSave_ = 0;
};
