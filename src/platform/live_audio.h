#pragma once
#include <stdint.h>

// ADC sampling + windowed RMS from the Phase 1 prototype. Retained for
// sub-project 3 (live signal detection); not wired into the brain yet.
class LiveAudio {
 public:
  void  begin();
  void  poll();               // call often; samples at 8 kHz
  float rms() const { return rms_; }

 private:
  uint32_t nextSampleUs_ = 0;
  uint64_t sumSquares_   = 0;
  uint32_t count_        = 0;
  float    dc_           = 2048.0f;
  float    rms_          = 0.0f;
};
