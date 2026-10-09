#include "performer.h"

void Performer::reset(Mood mood, uint32_t now) {
  reaction_ = -1;
  trigger_ = Trigger::None;
  startIdle(mood, now);
}

bool Performer::canInterrupt(Trigger t, uint32_t now) const {
  if (!playing()) return true;
  if (trigger_ == Trigger::Wake) return false;
  if (trigger_ == Trigger::DriftOff) return true;
  if (priority(t) <= priority(trigger_)) return false;
  return now - reactionStart_ >= cfg_.interruptGuardMs;
}

void Performer::start(int reaction, Trigger t, uint32_t now) {
  reaction_ = reaction;
  trigger_ = t;
  reactionStart_ = now;
  seen_ = 0;
  enterStep(0, now);
}

void Performer::extend(uint32_t now) {
  if (playing()) stepStart_ = now;
}

void Performer::onEvent(EventType e) {
  if (playing()) seen_ |= eventBit(e);
}

void Performer::onPick(float strength, uint32_t now) {
  if (playing()) return;
  if (idleMood_ != Mood::IntoIt && idleMood_ != Mood::Hyped) return;
  picks_++;
  bool qualifies = strength >= cfg_.strongPick || picks_ >= 2;
  if (!qualifies || now - lastIdleStep_ < cfg_.beatMinGapMs) return;
  advanceIdle(now);
  lastBeat_ = now;
  picks_ = 0;
}

void Performer::tick(Mood mood, uint32_t now) {
  if (playing()) {
    const Reaction& r = art_.reactions[reaction_];
    const Step& s = art_.steps[r.firstStep + step_];
    uint32_t elapsed = now - stepStart_;
    if (elapsed < stepHold_) return;
    bool waiting = s.until != EventType::None && !(seen_ & eventBit(s.until));
    if (waiting && elapsed < s.untilMax) return;
    if (step_ + 1 < r.stepCount) { enterStep(step_ + 1, now); return; }
    reaction_ = -1;
    trigger_ = Trigger::None;
    startIdle(mood, now);
    return;
  }
  if (mood != idleMood_) { startIdle(mood, now); return; }
  bool beat = mood == Mood::IntoIt || mood == Mood::Hyped;
  if (beat && now - lastBeat_ < cfg_.beatFallbackMs) return;
  if (now - lastIdleStep_ >= idlePeriod_) advanceIdle(now);
}

void Performer::enterStep(uint8_t i, uint32_t now) {
  const Step& s = art_.steps[art_.reactions[reaction_].firstStep + i];
  step_ = i;
  stepStart_ = now;
  stepHold_ = rng_.range(s.holdMin, s.holdMax);
  if (s.pose != POSE_CURRENT) pose_ = s.pose;
  eyes_ = s.eyes;
}

void Performer::startIdle(Mood mood, uint32_t now) {
  idleMood_ = mood;
  idleIdx_ = 0;
  picks_ = 0;
  pose_ = art_.idlePoses[art_.idles[(int)mood].first];
  eyes_ = Eye::Auto;
  lastIdleStep_ = lastBeat_ = now;
  idlePeriod_ = periodFor(mood);
}

void Performer::advanceIdle(uint32_t now) {
  const IdleLoop& l = art_.idles[(int)idleMood_];
  idleIdx_ = (idleIdx_ + 1) % l.count;
  pose_ = art_.idlePoses[l.first + idleIdx_];
  lastIdleStep_ = now;
  idlePeriod_ = periodFor(idleMood_);
}

uint32_t Performer::periodFor(Mood m) {
  switch (m) {
    case Mood::Asleep:  return rng_.jitter(cfg_.asleepIdleMs, 0.2f);
    case Mood::Curious: return rng_.jitter(cfg_.curiousIdleMs, 0.2f);
    case Mood::IntoIt:  return cfg_.intoItIdleMs;
    default:            return cfg_.hypedIdleMs;
  }
}
