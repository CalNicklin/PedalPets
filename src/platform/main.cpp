#include <Arduino.h>
#include <esp_system.h>
#include "core/brain.h"
#include "core/eyes.h"
#include "core/performer.h"
#include "core/timing.h"
#include "gen/pack.h"
#include "platform/mock_input.h"
#include "platform/renderer_tft.h"
#if PEDALPETS_DOLL
#include "platform/doll_pet.h"
#include "platform/doll_telemetry.h"
#if __has_include("gen/scene.h")
#include "gen/scene.h"
#endif
#else
#include "gen/pose_meta.h"
#endif

namespace {
const char* const MOOD_NAMES[] = {"Asleep", "Curious", "IntoIt", "Hyped"};

Rng           rng(1);
#if PEDALPETS_DOLL
DollPet       pet(rng);
char          line[1024];
#else
Performer     performer(gen::ART, rng);
Brain         brain(gen::ART, rng, performer);
EyeController eyes(rng);
#endif
MockInput     mock;
RendererTft   renderer;
bool          hud = false;
bool          telemetry = false;  // one CSV line per frame, for tools/render_timeline.py
uint32_t      nextTick = 0;   // fixed grid: logic every TICK_MS, render every 3rd tick
uint32_t      tickCount = 0;

void resetAll(uint32_t now) {
  mock.reset();
#if PEDALPETS_DOLL
#if PEDALPETS_SCENE
  pet.reset(now, scene_gen::LEAF_COLOURS, TELEMETRY_LEAVES);
#else
  pet.reset(now, 0, 0);
#endif
#else
  brain.reset(now);
  eyes.reset(now);
#endif
}

#if PEDALPETS_DOLL
// Logic tick for the paper doll: music in, mood and mind updated.
void dollTick(uint32_t t) {
  MusicEvent e;
  while (mock.pop(t, e)) pet.event(e, t);
  pet.tick(mock.features(t), t);
}

void dollFrame(uint32_t t, uint32_t now) {
  pet.frame(t);
#if PEDALPETS_SCENE
  const LeafField* scene = &pet.leaves;
  const float feetY = scene_gen::FEET_Y;
  auto leafSprite = [](int i) {
    const Leaf& l = pet.leaves.leaf(i);
    return scene_gen::leafSprite(l.colour, pet.leaves.rotation(i, scene_gen::LEAF_ROTATIONS), pet.leaves.edgeOn(i));
  };
#else
  const LeafField* scene = nullptr;
  const float feetY = 0;
  auto leafSprite = [](int) { return -1; };
#endif
  int rx = pet.choreo.reaction();
  HudInfo info = {MOOD_NAMES[(int)pet.mood.mood()], pet.mood.energy(),
                  rx >= 0 ? doll_gen::MOVE_NAMES[rx] : nullptr, 0};
  uint32_t start = micros();
  renderer.drawDoll(pet.parts, pet.marks, pet.markCount, scene, hud ? &info : nullptr);
  if (telemetry) {
    dollTelemetryRow(line, sizeof(line), now, (int)pet.mood.mood(), pet.mood.energy(), info.reaction,
                     pet.mind.thought(), (long)(micros() - start), pet.parts, doll_gen::PART_COUNT, pet.marks,
                     pet.markCount, scene, feetY, leafSprite);
    Serial.print("D,");
    Serial.println(line);
  }
}
#endif
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
  if (mock.takeTelemetryToggle()) {
    telemetry = !telemetry;
#if PEDALPETS_DOLL
    if (telemetry) {
      dollTelemetryHeader(line, sizeof(line), doll_gen::PART_COUNT);
      Serial.print("H,");
      Serial.println(line);
    }
#endif
  }

  if ((int32_t)(now - nextTick) < 0) return;
  if (now - nextTick > 100) nextTick = now;  // fell far behind (e.g. serial burst): resync
  uint32_t t = nextTick;                      // logic runs on the grid, not on millis() jitter
  nextTick += TICK_MS;

  mock.tick(t);
#if PEDALPETS_DOLL
  dollTick(t);
  if (++tickCount % TICKS_PER_FRAME == 0) dollFrame(t, now);
#else
  MusicEvent e;
  while (mock.pop(t, e)) brain.onEvent(e, t);
  brain.tick(mock.features(t), t);
  eyes.tick(brain.mood(), performer.eyes(), t);

  if (++tickCount % TICKS_PER_FRAME == 0) {
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
#endif
}
