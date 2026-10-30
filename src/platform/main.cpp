#include <Arduino.h>
#include <esp_system.h>
#include "core/brain.h"
#include "core/eyes.h"
#include "core/performer.h"
#include "gen/pose_meta.h"
#include "platform/mock_input.h"
#include "platform/renderer_tft.h"

namespace {
constexpr uint32_t TICK_MS  = 10;  // input, mood, performer, eyes at 100 Hz
constexpr uint32_t FRAME_MS = 33;  // render at ~30 fps

const char* const MOOD_NAMES[] = {"Asleep", "Curious", "IntoIt", "Hyped"};

Rng           rng(1);
Performer     performer(gen::ART, rng);
Brain         brain(gen::ART, rng, performer);
EyeController eyes(rng);
MockInput     mock;
RendererTft   renderer;
bool          hud = false;
bool          telemetry = false;  // one CSV line per frame, for tools/render_timeline.py
uint32_t      lastTick = 0, lastFrame = 0;

void resetAll(uint32_t now) {
  mock.reset();
  brain.reset(now);
  eyes.reset(now);
}
}  // namespace

void setup() {
  Serial.setTxBufferSize(1024);  // telemetry lines must not block the loop
  Serial.begin(115200);
  rng = Rng(esp_random());
  renderer.begin();
  resetAll(millis());
  Serial.println("PedalPets ready. Keys: p P h f s S w W c + - 0 | 1-3 scripts | d HUD | t telemetry | r reset");
}

void loop() {
  uint32_t now = millis();
  while (Serial.available()) mock.key((char)Serial.read(), now);
  if (mock.takeReset()) resetAll(now);
  if (mock.takeHudToggle()) hud = !hud;
  if (mock.takeTelemetryToggle()) telemetry = !telemetry;

  if (now - lastTick >= TICK_MS) {
    lastTick = now;
    mock.tick(now);
    MusicEvent e;
    while (mock.pop(now, e)) brain.onEvent(e, now);
    brain.tick(mock.features(now), now);
    eyes.tick(brain.mood(), performer.eyes(), now);
  }

  if (now - lastFrame >= FRAME_MS) {
    lastFrame = now;
    HudInfo info = {
      MOOD_NAMES[(int)brain.mood()],
      brain.energy(),
      performer.playing() ? gen::REACTION_IDS[performer.reaction()] : nullptr,
      performer.step(),
    };
    uint32_t start = micros();
    renderer.draw(performer.pose(), eyes.eye(), hud ? &info : nullptr);
    if (telemetry) {
      Serial.printf("T,%u,%u,%d,%d,%.3f,%s,%d,%u\n", now, performer.pose(), (int)eyes.eye(),
                    (int)brain.mood(), brain.energy(), info.reaction ? info.reaction : "-",
                    performer.step(), micros() - start);
    }
  }
}
