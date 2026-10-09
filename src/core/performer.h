#pragma once
#include <stdint.h>
#include "art_tables.h"
#include "rng.h"

struct PerformerConfig {
  uint32_t interruptGuardMs = 120;
  uint32_t asleepIdleMs     = 900;   // ±20 % jitter
  uint32_t curiousIdleMs    = 700;   // ±20 % jitter
  uint32_t intoItIdleMs     = 500;   // timer fallback period
  uint32_t hypedIdleMs      = 400;   // timer fallback period
  uint32_t beatFallbackMs   = 1500;  // no beat-step for this long → timer
  uint32_t beatMinGapMs     = 250;
  float    strongPick       = 0.5f;
};

// Plays reactions (sequences of key poses) and mood idles. Decides nothing
// about *which* reaction — that is the Brain's job.
class Performer {
 public:
  Performer(const ArtTables& art, Rng& rng, const PerformerConfig& cfg = PerformerConfig())
      : art_(art), rng_(rng), cfg_(cfg) {}

  void reset(Mood mood, uint32_t now);

  bool     playing()  const { return reaction_ >= 0; }
  int      reaction() const { return reaction_; }
  Trigger  trigger()  const { return trigger_; }
  uint8_t  step()     const { return step_; }
  uint16_t pose()     const { return pose_; }
  Eye      eyes()     const { return eyes_; }   // Auto unless a step overrides

  bool canInterrupt(Trigger t, uint32_t now) const;
  void start(int reaction, Trigger t, uint32_t now);
  void extend(uint32_t now);                  // restart current step's hold
  void onEvent(EventType e);                  // feeds `until`
  void onPick(float strength, uint32_t now);  // beat-step idle
  void tick(Mood mood, uint32_t now);

 private:
  void     enterStep(uint8_t i, uint32_t now);
  void     startIdle(Mood mood, uint32_t now);
  void     advanceIdle(uint32_t now);
  uint32_t periodFor(Mood m);

  const ArtTables& art_;
  Rng&             rng_;
  PerformerConfig  cfg_;

  int      reaction_      = -1;
  Trigger  trigger_       = Trigger::None;
  uint8_t  step_          = 0;
  uint32_t reactionStart_ = 0;
  uint32_t stepStart_     = 0;
  uint32_t stepHold_      = 0;
  uint16_t seen_          = 0;   // eventBit()s seen since reaction start

  uint16_t pose_ = 0;
  Eye      eyes_ = Eye::Auto;

  Mood     idleMood_     = Mood::Asleep;
  uint8_t  idleIdx_      = 0;
  uint8_t  picks_        = 0;
  uint32_t lastIdleStep_ = 0;
  uint32_t lastBeat_     = 0;
  uint32_t idlePeriod_   = 0;
};
