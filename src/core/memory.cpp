#include "memory.h"
#include <math.h>

void Bond::load(const PlayerMemory& m) {
  mem_ = m.version == PLAYER_MEMORY_VERSION ? m : PlayerMemory();
  playAtSave_ = mem_.playSeconds;
  msPlay_ = msHyped_ = 0;
  sessionUnsaved_ = false;
}

void Bond::onWake(uint32_t now) {
  (void)now;
  mem_.sessions++;
  sessionUnsaved_ = true;
}

void Bond::onEvent(const MusicEvent& e, uint32_t now) {
  if (e.type == EventType::Pick || e.type == EventType::BigHit || e.type == EventType::Flurry) {
    lastNote_ = now;
    heard_ = true;
  }
}

void Bond::tick(Mood mood, uint32_t now) {
  uint32_t dt = lastTick_ ? now - lastTick_ : 0;
  lastTick_ = now;
  if (!heard_ || now - lastNote_ > cfg_.playingMs) return;     // only time spent playing together counts
  msPlay_ += dt;
  if (mood == Mood::Hyped) msHyped_ += dt;
  while (msPlay_ >= 1000) { msPlay_ -= 1000; mem_.playSeconds++; }
  while (msHyped_ >= 1000) { msHyped_ -= 1000; mem_.hypedSeconds++; }
}

float Bond::familiarity() const {
  return 1.0f - expf(-(float)mem_.playSeconds / cfg_.friendSeconds);
}

bool Bond::wantsSave(uint32_t now) const {
  (void)now;
  return sessionUnsaved_ || mem_.playSeconds - playAtSave_ >= cfg_.saveEverySec;
}

void Bond::saved(uint32_t now) {
  (void)now;
  sessionUnsaved_ = false;
  playAtSave_ = mem_.playSeconds;
}
