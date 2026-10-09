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
