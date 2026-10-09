#include "eyes.h"

void EyeController::reset(uint32_t now) {
  asleep_ = false;
  eye_ = Eye::Open;
  schedule(now);
}

void EyeController::schedule(uint32_t now) {
  action_ = Eye::Open;
  nextBlink_ = now + rng_.range(cfg_.blinkEveryMin, cfg_.blinkEveryMax);
  nextGlance_ = now + rng_.range(cfg_.glanceEveryMin, cfg_.glanceEveryMax);
}

void EyeController::tick(Mood mood, Eye stepOverride, uint32_t now) {
  if (mood == Mood::Asleep) {  // Asleep poses have baked eyes
    asleep_ = true;
    eye_ = Eye::Open;
    return;
  }
  if (asleep_) { asleep_ = false; schedule(now); }

  if (action_ != Eye::Open && due(now, actionEnd_)) action_ = Eye::Open;
  if (action_ == Eye::Open) {
    if (due(now, nextBlink_)) {
      action_ = Eye::Blink;
      actionEnd_ = now + cfg_.blinkMs;
      nextBlink_ = now + rng_.range(cfg_.blinkEveryMin, cfg_.blinkEveryMax);
    } else if (due(now, nextGlance_)) {
      action_ = rng_.range(0, 1) ? Eye::LookL : Eye::LookR;
      actionEnd_ = now + rng_.range(cfg_.glanceMin, cfg_.glanceMax);
      nextGlance_ = now + rng_.range(cfg_.glanceEveryMin, cfg_.glanceEveryMax);
    }
  }
  eye_ = stepOverride != Eye::Auto ? stepOverride : action_;
}
