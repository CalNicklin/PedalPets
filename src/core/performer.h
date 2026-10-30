#pragma once
#include <stdint.h>
#include "art_tables.h"
#include "rng.h"
#include "timing.h"

struct PerformerConfig {
  uint32_t interruptGuardMs = 120;
  float    idleSpeedup      = 0.6f;  // idle cycle rate × (1 + idleSpeedup × energy)
  float    speedHysteresis  = 0.6f;  // frames the ideal hold must drift before it changes
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
  void extend(uint32_t now);                  // repeat loop section, else restart current hold
  void onEvent(EventType e);                  // feeds `until`
  void tick(Mood mood, float energy, uint32_t now);

 private:
  void enterStep(uint8_t i, uint32_t now);
  void startIdle(Mood mood, float energy, uint32_t now);
  void tickIdle(Mood mood, float energy, uint32_t now);
  void updateIdleFrames(float energy);

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
  bool     extendPending_ = false;

  uint16_t pose_ = 0;
  Eye      eyes_ = Eye::Auto;

  Mood     idleMood_     = Mood::Asleep;
  uint8_t  idleIdx_      = 0;
  uint32_t idleFrames_   = 1;   // frames each idle pose is held, at current speed
  uint32_t lastIdleStep_ = 0;
};
