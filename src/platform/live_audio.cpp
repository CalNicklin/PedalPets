#include "live_audio.h"
#include <Arduino.h>

namespace {
constexpr int      AUDIO_PIN      = 34;
constexpr int      SAMPLE_HZ      = 8000;
constexpr int      WINDOW_MS      = 50;
constexpr int      WINDOW_SAMPLES = SAMPLE_HZ * WINDOW_MS / 1000;
constexpr uint32_t SAMPLE_US      = 1000000UL / SAMPLE_HZ;
}  // namespace

void LiveAudio::begin() {
  analogReadResolution(12);
  analogSetPinAttenuation(AUDIO_PIN, ADC_11db);
  nextSampleUs_ = micros();
}

void LiveAudio::poll() {
  if ((int32_t)(micros() - nextSampleUs_) < 0) return;
  nextSampleUs_ += SAMPLE_US;
  int raw = analogRead(AUDIO_PIN);
  dc_ += (raw - dc_) * 0.0005f;
  float ac = raw - dc_;
  sumSquares_ += (uint32_t)(ac * ac);
  if (++count_ >= WINDOW_SAMPLES) {
    rms_ = sqrtf((float)sumSquares_ / count_);
    sumSquares_ = 0;
    count_ = 0;
  }
}
