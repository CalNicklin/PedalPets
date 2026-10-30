#include "performer.h"
#include <math.h>

void Performer::reset(Mood mood, uint32_t now) {
  reaction_ = -1;
  trigger_ = Trigger::None;
  startIdle(mood, 0.0f, now);
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

void Performer::tick(Mood mood, float energy, uint32_t now) {
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
    startIdle(mood, energy, now);
    return;
  }
  tickIdle(mood, energy, now);
}

// Continuous cycle, each pose held a whole number of frames. Energy speeds
// the cycle up in whole-frame steps (with hysteresis, so it doesn't flip
// between two speeds). A mood change waits for the current pose to finish.
void Performer::tickIdle(Mood mood, float energy, uint32_t now) {
  if (now - lastIdleStep_ < idleFrames_ * FRAME_MS) return;
  if (mood != idleMood_) { startIdle(mood, energy, now); return; }
  const IdleLoop& l = art_.idles[(int)idleMood_];
  idleIdx_ = (idleIdx_ + 1) % l.count;
  pose_ = art_.idlePoses[l.first + idleIdx_];
  lastIdleStep_ = now;
  updateIdleFrames(energy);
}

void Performer::updateIdleFrames(float energy) {
  const IdleLoop& l = art_.idles[(int)idleMood_];
  float ideal = l.periodMs / (FRAME_MS * (1.0f + cfg_.idleSpeedup * energy));
  if (fabsf(ideal - idleFrames_) > cfg_.speedHysteresis)
    idleFrames_ = ideal < 1.5f ? 1 : (uint32_t)lroundf(ideal);
}

void Performer::enterStep(uint8_t i, uint32_t now) {
  const Step& s = art_.steps[art_.reactions[reaction_].firstStep + i];
  step_ = i;
  stepStart_ = now;
  stepHold_ = toFrames(rng_.range(s.holdMin, s.holdMax)) * FRAME_MS;
  if (s.pose != POSE_CURRENT) pose_ = s.pose;
  eyes_ = s.eyes;
}

void Performer::startIdle(Mood mood, float energy, uint32_t now) {
  idleMood_ = mood;
  idleIdx_ = 0;
  idleFrames_ = 0;  // force updateIdleFrames to take the current speed
  updateIdleFrames(energy);
  lastIdleStep_ = now;
  pose_ = art_.idlePoses[art_.idles[(int)mood].first];
  eyes_ = Eye::Auto;
}
