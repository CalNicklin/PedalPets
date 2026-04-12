#include <Arduino.h>

// Phase 1 bench test: audio sampling + state machine, no display yet.
// Reads ADC on GPIO 34, computes rolling RMS, classifies into IDLE/AWAKE/
// ROCKING, prints a VU bar + state to serial.

constexpr int   AUDIO_PIN      = 34;
constexpr int   SAMPLE_HZ      = 8000;
constexpr int   WINDOW_MS      = 50;
constexpr int   WINDOW_SAMPLES = SAMPLE_HZ * WINDOW_MS / 1000; // 400
constexpr uint32_t SAMPLE_US   = 1000000UL / SAMPLE_HZ;

// Thresholds in raw ADC units (12-bit, 0..4095, DC-biased ~2048).
// Tune on real hardware — these are placeholders.
constexpr float LOW_THRESHOLD  = 80.0f;
constexpr float HIGH_THRESHOLD = 400.0f;

// Release (slow calm-down) and attack (fast wake-up) in ms.
constexpr uint32_t RELEASE_MS  = 2000;
constexpr uint32_t ATTACK_MS   = 30;

enum State { IDLE, AWAKE, ROCKING };
const char* stateName(State s) {
  switch (s) { case IDLE: return "IDLE"; case AWAKE: return "AWAKE"; case ROCKING: return "ROCKING"; }
  return "?";
}

State    state          = IDLE;
uint32_t lastTransition = 0;
uint32_t lastPrint      = 0;

// Sampling state
uint32_t nextSampleUs = 0;
uint64_t sumSquares   = 0;
uint32_t sampleCount  = 0;
float    dcEstimate   = 2048.0f; // adaptive DC bias tracking
float    currentRms   = 0.0f;

void updateState(float rms, uint32_t now) {
  State target = state;

  if (rms > HIGH_THRESHOLD)      target = ROCKING;
  else if (rms > LOW_THRESHOLD)  target = (state == ROCKING) ? ROCKING : AWAKE;
  else                           target = IDLE;

  // Attack: jump up immediately. Release: require sustained quiet.
  if (target > state) {
    if (now - lastTransition >= ATTACK_MS) {
      state = target;
      lastTransition = now;
    }
  } else if (target < state) {
    if (now - lastTransition >= RELEASE_MS) {
      state = (State)(state - 1); // step down one level
      lastTransition = now;
    }
  } else {
    lastTransition = now; // staying at target — reset timer
  }
}

void printVU(float rms, State s) {
  int bars = min(40, (int)(rms / 20.0f));
  Serial.printf("%-8s [%4.0f] ", stateName(s), rms);
  for (int i = 0; i < bars; i++) Serial.print('#');
  for (int i = bars; i < 40; i++) Serial.print(' ');
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(AUDIO_PIN, ADC_11db); // ~0-3.3V range
  nextSampleUs = micros();
  Serial.println("PedalPets bench: audio sampling on GPIO 34");
}

void loop() {
  uint32_t now = millis();

  // Sample at fixed rate.
  if ((int32_t)(micros() - nextSampleUs) >= 0) {
    nextSampleUs += SAMPLE_US;
    int raw = analogRead(AUDIO_PIN);

    // Slow DC tracker (~1Hz cutoff) so we follow the bias point over time.
    dcEstimate += (raw - dcEstimate) * 0.0005f;
    float ac = raw - dcEstimate;
    sumSquares += (uint32_t)(ac * ac);
    sampleCount++;

    if (sampleCount >= WINDOW_SAMPLES) {
      currentRms = sqrtf((float)sumSquares / sampleCount);
      sumSquares = 0;
      sampleCount = 0;
      updateState(currentRms, now);
    }
  }

  // Print at 10Hz for readable serial output.
  if (now - lastPrint >= 100) {
    lastPrint = now;
    printVU(currentRms, state);
  }
}
