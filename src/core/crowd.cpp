#include "crowd.h"

void Crowd::reset(int count, uint32_t now) {
  count_ = count > CROWD_MAX ? CROWD_MAX : count;
  for (int i = 0; i < count_; i++) {
    c_[i] = Critter();
    c_[i].shyness = 0.15f + 0.6f * (float)(rng_.next() % 1000) / 999.0f;
  }
  now_ = now;
  duckUntil_ = 0;
  nextSleepPeek_ = now + rng_.range(cfg_.sleepPeekMinMs, cfg_.sleepPeekMaxMs);
}

void Crowd::onEvent(const MusicEvent& e, uint32_t now) {
  if (e.type == EventType::BigHit) {
    duckUntil_ = now + cfg_.duckMs;
    return;
  }
  if (e.type != EventType::Pick) return;
  for (int i = 0; i < count_; i++) {                 // bob along, not all on every beat
    Critter& c = c_[i];
    if (c.pose == CritterPose::Up || c.pose == CritterPose::Cheer)
      if (rng_.next() % 4 != 0) c.bobUntil = now + cfg_.bobMs;
  }
  if (hyped_) {                                       // and cheer on some beats
    int i = (int)(rng_.next() % (count_ ? count_ : 1));
    if (c_[i].pose == CritterPose::Up) c_[i].pose = CritterPose::Cheer;
    else if (c_[i].pose == CritterPose::Cheer) c_[i].pose = CritterPose::Up;
  }
}

void Crowd::tick(Mood mood, float energy, uint32_t now) {
  now_ = now;
  hyped_ = mood == Mood::Hyped;
  // How much the music draws them out: nobody while it sleeps, a few curious
  // ones when it's quiet, everyone when it's going.
  float draw = mood == Mood::Asleep ? 0.0f : mood == Mood::Curious ? 0.35f : 0.6f + 0.6f * energy;
  bool ducking = duckUntil_ && (int32_t)(now - duckUntil_) < 0;

  if (mood == Mood::Asleep && (int32_t)(now - nextSleepPeek_) >= 0 && count_) {
    Critter& c = c_[rng_.next() % count_];           // one peeks out, then hides again
    c.peekUntil = now + cfg_.sleepPeekLenMs;
    nextSleepPeek_ = now + rng_.range(cfg_.sleepPeekMinMs, cfg_.sleepPeekMaxMs);
  }

  for (int i = 0; i < count_; i++) {
    Critter& c = c_[i];
    bool want = draw > c.shyness;
    if (want != c.out && !c.changeAt) c.changeAt = now + rng_.range(0, cfg_.staggerMaxMs);
    if (c.changeAt && (int32_t)(now - c.changeAt) >= 0) {
      c.changeAt = 0;
      if (want != c.out) {
        c.out = want;
        c.outSince = now;
      }
    }
    if (!c.out) {
      bool peeking = c.peekUntil && (int32_t)(now - c.peekUntil) < 0;
      c.pose = peeking ? CritterPose::Peek : CritterPose::Hidden;
      continue;
    }
    if (ducking || now - c.outSince < cfg_.peekMs) c.pose = CritterPose::Peek;   // eyes first
    else if (c.pose == CritterPose::Hidden || c.pose == CritterPose::Peek) c.pose = CritterPose::Up;
    if (!hyped_ && c.pose == CritterPose::Cheer) c.pose = CritterPose::Up;
  }
}
