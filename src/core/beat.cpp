#include "beat.h"
#include <math.h>

void BeatClock::reset(uint32_t now, uint32_t periodMs) {
  period_ = (float)periodMs;
  confidence_ = 0;
  lastBeat_ = (float)now;
  nextBeat_ = now + period_;
  count_ = 0;
  lastOnset_ = lastTick_ = now;
  heard_ = false;
}

void BeatClock::setTempo(uint32_t periodMs) {
  if (confidence_ < 0.3f) period_ += ((float)periodMs - period_) * 0.05f;   // drift to it gently
}

float BeatClock::fold(float ioi) const {
  while (ioi < cfg_.minPeriodMs) ioi *= 2;   // eighths and sixteenths: the beat is longer
  while (ioi > cfg_.maxPeriodMs) ioi /= 2;   // half notes: the beat is shorter
  return ioi;
}

void BeatClock::onOnset(uint32_t now) {
  float t = (float)now;
  // Which beat is it near? The one just gone, or the one coming.
  float before = t - lastBeat_, after = nextBeat_ - t;
  bool toPrev = before <= after;
  float err = toPrev ? before : -after;      // + late, - early
  bool near = fabsf(err) <= cfg_.window * period_;
  // A note halfway between beats is a fine subdivision, neither for nor against.
  float half = fabsf(fabsf(err) - period_ / 2);
  bool offbeat = half <= cfg_.window * period_ / 2;

  if (confidence_ < 0.25f && !near) {
    // Not locked yet: take this note as a beat and see if the next ones agree.
    lastBeat_ = t;
    nextBeat_ = t + period_;
  } else if (near) {
    lastBeat_ += err * cfg_.phaseGain;
    nextBeat_ += err * cfg_.phaseGain;
    period_ += err * cfg_.periodGain;
    confidence_ += (1 - confidence_) * cfg_.trust;
  } else if (!offbeat) {
    confidence_ -= confidence_ * cfg_.trust;
  }
  // Finding the tempo: while unsure, steer towards the spacing of the notes.
  if (heard_ && confidence_ < 0.5f) {
    float ioi = (float)(now - lastOnset_);
    if (ioi > 120 && ioi < 2500) period_ += (fold(ioi) - period_) * 0.35f;
  }
  if (period_ < cfg_.minPeriodMs) period_ = (float)cfg_.minPeriodMs;
  if (period_ > cfg_.maxPeriodMs) period_ = (float)cfg_.maxPeriodMs;
  nextBeat_ = lastBeat_ + period_;
  lastOnset_ = now;
  heard_ = true;
}

bool BeatClock::tick(uint32_t now) {
  float dt = (float)(now - lastTick_);
  lastTick_ = now;
  if (now - lastOnset_ > 400) confidence_ -= confidence_ * dt / cfg_.fadeMs;   // no notes: less sure
  if ((float)now < nextBeat_) return false;
  lastBeat_ = nextBeat_;
  nextBeat_ += period_;
  count_++;
  return true;
}

float BeatClock::phase(uint32_t now) const {
  float p = ((float)now - lastBeat_) / period_;
  return p < 0 ? 0 : p >= 1 ? 0.999f : p;
}
