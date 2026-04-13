#include <Arduino.h>
#include <TFT_eSPI.h>
#include "sprites/sprite_idle.h"
#include "sprites/sprite_run.h"
#include "sprites/sprite_attack.h"

// --- audio sampling -------------------------------------------------------
constexpr int   AUDIO_PIN      = 34;
constexpr int   SAMPLE_HZ      = 8000;
constexpr int   WINDOW_MS      = 50;
constexpr int   WINDOW_SAMPLES = SAMPLE_HZ * WINDOW_MS / 1000;
constexpr uint32_t SAMPLE_US   = 1000000UL / SAMPLE_HZ;
constexpr float LOW_THRESHOLD  = 80.0f;
constexpr float HIGH_THRESHOLD = 400.0f;
constexpr uint32_t RELEASE_MS  = 2000;
constexpr uint32_t ATTACK_MS   = 30;

enum State { IDLE, AWAKE, ROCKING };

State    state           = IDLE;
uint32_t lastTransition  = 0;
uint32_t nextSampleUs    = 0;
uint64_t sumSquares      = 0;
uint32_t sampleCount     = 0;
float    dcEstimate      = 2048.0f;
float    currentRms      = 0.0f;

// --- display --------------------------------------------------------------
TFT_eSPI tft = TFT_eSPI();
TFT_eSprite canvas = TFT_eSprite(&tft);
constexpr uint16_t SCREEN_W = 160;
constexpr uint16_t SCREEN_H = 128;
constexpr uint16_t BG_COLOR = TFT_BLACK;

constexpr uint32_t FRAME_MS = 125;       // 8fps
uint32_t lastFrameMs       = 0;
uint8_t  frameIdx          = 0;
State    renderedState     = (State)-1;  // force first draw

struct Anim {
  uint16_t w, h, frames;
  const uint16_t *data;
};
const Anim ANIMS[] = {
  { IDLE_W,   IDLE_H,   IDLE_FRAMES,   IDLE_DATA   },
  { RUN_W,    RUN_H,    RUN_FRAMES,    RUN_DATA    },
  { ATTACK_W, ATTACK_H, ATTACK_FRAMES, ATTACK_DATA },
};

void updateState(float rms, uint32_t now) {
  State target = state;
  if (rms > HIGH_THRESHOLD)     target = ROCKING;
  else if (rms > LOW_THRESHOLD) target = (state == ROCKING) ? ROCKING : AWAKE;
  else                          target = IDLE;

  if (target > state) {
    if (now - lastTransition >= ATTACK_MS) { state = target; lastTransition = now; }
  } else if (target < state) {
    if (now - lastTransition >= RELEASE_MS) { state = (State)(state - 1); lastTransition = now; }
  } else { lastTransition = now; }
}

void drawFrame() {
  const Anim &a = ANIMS[state];
  int16_t x = (SCREEN_W - a.w) / 2;
  int16_t y = (SCREEN_H - a.h) / 2;
  canvas.fillSprite(BG_COLOR);
  canvas.pushImage(x, y, a.w, a.h, (uint16_t*)(a.data + (uint32_t)frameIdx * a.w * a.h));
  canvas.pushSprite(0, 0);
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(AUDIO_PIN, ADC_11db);
  nextSampleUs = micros();

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(BG_COLOR);
  canvas.setColorDepth(16);
  canvas.createSprite(SCREEN_W, SCREEN_H);
  canvas.setSwapBytes(true);
  Serial.println("PedalPets ready");
}

void loop() {
  uint32_t now = millis();

  // Audio sample at fixed rate
  if ((int32_t)(micros() - nextSampleUs) >= 0) {
    nextSampleUs += SAMPLE_US;
    int raw = analogRead(AUDIO_PIN);
    dcEstimate += (raw - dcEstimate) * 0.0005f;
    float ac = raw - dcEstimate;
    sumSquares += (uint32_t)(ac * ac);
    if (++sampleCount >= WINDOW_SAMPLES) {
      currentRms = sqrtf((float)sumSquares / sampleCount);
      sumSquares = 0; sampleCount = 0;
      updateState(currentRms, now);
    }
  }

  // Animate at 8fps
  if (now - lastFrameMs >= FRAME_MS) {
    lastFrameMs = now;
    if (state != renderedState) { frameIdx = 0; renderedState = state; }
    else                        { frameIdx = (frameIdx + 1) % ANIMS[state].frames; }
    drawFrame();
  }
}
