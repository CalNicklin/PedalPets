#pragma once
#include <stdint.h>
#include "art_tables.h"
#include "rng.h"

struct EyeConfig {
  uint32_t blinkMs        = 120;
  uint32_t blinkEveryMin  = 2000, blinkEveryMax  = 6000;
  uint32_t glanceEveryMin = 4000, glanceEveryMax = 10000;
  uint32_t glanceMin      = 400,  glanceMax      = 800;
};

// Small, deliberate eye changes (blink, glance) that keep holds alive.
class EyeController {
 public:
  explicit EyeController(Rng& rng, const EyeConfig& cfg = EyeConfig()) : rng_(rng), cfg_(cfg) {}
  void reset(uint32_t now);
  void tick(Mood mood, Eye stepOverride, uint32_t now);
  Eye  eye() const { return eye_; }

 private:
  void schedule(uint32_t now);
  static bool due(uint32_t now, uint32_t at) { return (int32_t)(now - at) >= 0; }

  Rng&      rng_;
  EyeConfig cfg_;
  Eye       eye_        = Eye::Open;
  Eye       action_     = Eye::Open;  // Open, Blink, LookL or LookR
  uint32_t  actionEnd_  = 0;
  uint32_t  nextBlink_  = 0;
  uint32_t  nextGlance_ = 0;
  bool      asleep_     = false;
};
