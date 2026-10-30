#pragma once
#include <stdint.h>
#include "core/music_event.h"
#include "scripts.h"

// Keyboard / scripted stand-in for the live audio detectors.
// Keys: p P h f s S w W c + - 0 1-4 n b x g d t r (see key()).
class MockInput {
 public:
  void     reset();
  void     key(char c, uint32_t now);
  void     tick(uint32_t now);                      // advances a running script
  bool     pop(uint32_t now, MusicEvent& out);      // next due event, in order
  Features features(uint32_t now) const;
  bool     takeHudToggle() { bool r = hud_; hud_ = false; return r; }
  bool     takeReset()     { bool r = reset_; reset_ = false; return r; }
  bool     takeTelemetryToggle() { bool r = telemetry_; telemetry_ = false; return r; }
  bool     takeNextCharacter() { bool r = nextChar_; nextChar_ = false; return r; }
  bool     takeNextScene()     { bool r = nextScene_; nextScene_ = false; return r; }
  bool     takeForget()        { bool r = forget_; forget_ = false; return r; }
  bool     takeDirector()      { bool r = director_; director_ = false; return r; }

 private:
  void  schedule(EventType type, float strength, uint32_t at);
  void  runScript(int n, uint32_t now);
  void  lift(float level, uint32_t now);
  float liftNow(uint32_t now) const;

  static constexpr int      QUEUE  = 32;
  static constexpr int      MAX_SCRIPT = 32;
  static constexpr uint32_t LIFT_MS = 300;

  MusicEvent queue_[QUEUE];
  int        count_ = 0;
  float      base_ = 0, lift_ = 0;
  uint32_t   liftAt_ = 0;
  const Script* script_ = nullptr;
  uint32_t   scriptStart_ = 0;
  uint16_t   fired_[MAX_SCRIPT] = {};
  bool       hud_ = false, reset_ = false, telemetry_ = false, nextChar_ = false, nextScene_ = false, forget_ = false, director_ = false;
};
