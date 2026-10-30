#include <Arduino.h>
#include <esp_system.h>
#include "core/timing.h"
#include "gen/packs.h"
#include "platform/doll_pet.h"
#include "platform/doll_telemetry.h"
#include "platform/mock_input.h"
#include "platform/renderer_tft.h"

namespace {
const char* const MOOD_NAMES[] = {"Asleep", "Curious", "IntoIt", "Hyped"};

Rng         rng(1);
DollPet     pet(*CHARACTERS[0], rng);
int         characterIndex = 0, sceneIndex = 0;
MockInput   mock;
RendererTft renderer;
bool        hud = false;
bool        telemetry = false;  // one CSV line per frame, for tools/doll_timeline.py
uint32_t    nextTick = 0;       // fixed grid: logic every TICK_MS, render every 3rd tick
uint32_t    tickCount = 0;
char        line[1024];

const Scene* currentScene() { return SCENE_COUNT ? SCENES[sceneIndex] : nullptr; }

void sendHeader() {
  dollTelemetryHeader(line, sizeof(line), pet.character().doll.partCount);
  Serial.print("H,");
  Serial.println(line);
}

void resetAll(uint32_t now) {
  mock.reset();
  pet.setCharacter(*CHARACTERS[characterIndex]);
  pet.setScene(currentScene());
  pet.reset(now, TELEMETRY_LEAVES);
  Serial.printf("character: %s  scene: %s\n", pet.character().name, currentScene() ? currentScene()->name : "-");
  if (telemetry) sendHeader();
}

void frame(uint32_t t, uint32_t now) {
  pet.frame(t);
  const Scene* scene = pet.scene();
  int rx = pet.choreo.reaction();
  HudInfo info = {MOOD_NAMES[(int)pet.mood.mood()], pet.mood.energy(),
                  rx >= 0 ? pet.character().moveNames[rx] : nullptr, pet.mind.thought()};
  uint32_t start = micros();
  renderer.drawDoll(pet.character(), scene, pet.parts, pet.marks, pet.markCount, &pet.leaves, hud ? &info : nullptr);
  if (telemetry) {
    auto sprite = [scene](int i) {
      const Leaf& l = pet.leaves.leaf(i);
      return scene ? leafSprite(*scene, l.colour, pet.leaves.rotation(i, scene->leafRotations), pet.leaves.edgeOn(i))
                   : -1;
    };
    dollTelemetryRow(line, sizeof(line), now, (int)pet.mood.mood(), pet.mood.energy(), info.reaction,
                     info.thought, (long)(micros() - start), pet.parts, pet.character().doll.partCount, pet.marks,
                     pet.markCount, scene && scene->leafColours ? &pet.leaves : nullptr,
                     scene ? scene->feetY : 0, sprite);
    Serial.print("D,");
    Serial.println(line);
  }
}
}  // namespace

void setup() {
  Serial.setTxBufferSize(1024);  // telemetry lines must not block the loop
  Serial.begin(115200);
  rng = Rng(esp_random());
  renderer.begin();
  resetAll(millis());
  Serial.println("PedalPets ready. Keys: p P h f s S w W c + - 0 | 1-3 scripts | n character | b scene | "
                 "d HUD | t telemetry | r reset");
}

void loop() {
  uint32_t now = millis();
  while (Serial.available()) mock.key((char)Serial.read(), now);
  if (mock.takeNextCharacter()) {
    characterIndex = (characterIndex + 1) % CHARACTER_COUNT;
    resetAll(now);
  }
  if (mock.takeNextScene() && SCENE_COUNT) {
    sceneIndex = (sceneIndex + 1) % SCENE_COUNT;
    resetAll(now);
  }
  if (mock.takeReset()) resetAll(now);
  if (mock.takeHudToggle()) hud = !hud;
  if (mock.takeTelemetryToggle()) {
    telemetry = !telemetry;
    if (telemetry) sendHeader();
  }

  if ((int32_t)(now - nextTick) < 0) return;
  if (now - nextTick > 100) nextTick = now;  // fell far behind (e.g. serial burst): resync
  uint32_t t = nextTick;                      // logic runs on the grid, not on millis() jitter
  nextTick += TICK_MS;

  mock.tick(t);
  MusicEvent e;
  while (mock.pop(t, e)) pet.event(e, t);
  pet.tick(mock.features(t), t);
  if (++tickCount % TICKS_PER_FRAME == 0) frame(t, now);
}
