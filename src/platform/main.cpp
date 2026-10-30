#include <Arduino.h>
#include <Preferences.h>
#include <esp_system.h>
#include "core/timing.h"
#include "gen/packs.h"
#include "platform/doll_pet.h"
#include "platform/director_link.h"
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
Preferences prefs;              // the pet's memory of you, in flash (NVS)
DirectorLink director;
bool        directing = false;  // summaries out, suggestions in (tools/director.py)
char        inLine[96];         // a "#..." line coming in over serial
int         inLen = -1;         // -1: not collecting a line

void loadMemory() {
  PlayerMemory m;
  if (prefs.getBytesLength("mem") == sizeof(m)) prefs.getBytes("mem", &m, sizeof(m));
  pet.bond.load(m);
  Serial.printf("memory: %u sessions, %u s played, familiarity %.2f\n", (unsigned)pet.bond.memory().sessions,
                (unsigned)pet.bond.memory().playSeconds, pet.bond.familiarity());
}

void saveMemoryIfDue(uint32_t now) {
  if (!pet.bond.wantsSave(now)) return;
  prefs.putBytes("mem", &pet.bond.memory(), sizeof(PlayerMemory));
  pet.bond.saved(now);
}

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
  if (directing) {                                 // the director needs the new character's moves
    director.moves(line, sizeof(line), pet.character());
    Serial.println(line);
  }
}

void frame(uint32_t t, uint32_t now) {
  pet.frame(t);
  const Scene* scene = pet.scene();
  int rx = pet.choreo.reaction();
  HudInfo info = {MOOD_NAMES[(int)pet.mood.mood()], pet.mood.energy(),
                  rx >= 0 ? pet.character().moveNames[rx] : nullptr, pet.mind.thought()};
  CritterView crowd[CROWD_MAX];
  int crowdCount = pet.critters(crowd);
  Bubble bubble = {pet.mind.line(t), 0, 0};
  if (bubble.text) pet.headTop(&bubble.headX, &bubble.headY);
  uint32_t start = micros();
  renderer.drawDoll(pet.character(), scene, pet.parts, pet.marks, pet.markCount, &pet.leaves, crowd, crowdCount,
                    &bubble, hud ? &info : nullptr);
  if (telemetry) {
    auto sprite = [scene](int i) {
      const Leaf& l = pet.leaves.leaf(i);
      return scene ? leafSprite(*scene, l.colour, pet.leaves.rotation(i, scene->leafRotations), pet.leaves.edgeOn(i))
                   : -1;
    };
    dollTelemetryRow(line, sizeof(line), now, (int)pet.mood.mood(), pet.mood.energy(), info.reaction,
                     info.thought, (long)(micros() - start), pet.parts, pet.character().doll.partCount, pet.marks,
                     pet.markCount, scene && scene->leafColours ? &pet.leaves : nullptr,
                     scene ? scene->feetY : 0, sprite, crowd, crowdCount, bubble.text);
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
  prefs.begin("pedalpets", false);
  loadMemory();
  resetAll(millis());
  Serial.println("PedalPets ready. Keys: p P h f s S w W c + - 0 | 1-5 scripts | n character | b scene | "
                 "x forget me | g/G director on/off | d HUD | t telemetry | r reset");
}

namespace {
// Act on each key as it arrives, so "n1" switches character *then* starts
// script 1 (a reset after the script started would cancel it).
void handleKey(char c, uint32_t now) {
  if (inLen >= 0 || c == '#') {                    // a whole line from the director, not keys
    if (c == '\n' || c == '\r') {
      inLine[inLen < 0 ? 0 : inLen] = 0;
      if (inLen > 0 && director.apply(inLine, pet, now)) Serial.printf("directed: %s\n", inLine);
      inLen = -1;
    } else if (inLen < (int)sizeof(inLine) - 1) {
      inLine[inLen < 0 ? (inLen = 0) : inLen] = c;
      inLen++;
    }
    return;
  }
  mock.key(c, now);
  if (int d = mock.takeDirector()) {
    directing = d == 1;
    if (directing) {
      director.moves(line, sizeof(line), pet.character());
      Serial.println(line);
    }
  }
  if (mock.takeNextCharacter()) {
    characterIndex = (characterIndex + 1) % CHARACTER_COUNT;
    resetAll(now);
  }
  if (mock.takeNextScene() && SCENE_COUNT) {
    sceneIndex = (sceneIndex + 1) % SCENE_COUNT;
    resetAll(now);
  }
  if (mock.takeReset()) resetAll(now);
  if (mock.takeForget()) {
    pet.bond.load(PlayerMemory());
    prefs.putBytes("mem", &pet.bond.memory(), sizeof(PlayerMemory));
    Serial.println("memory: forgotten");
  }
  if (mock.takeHudToggle()) hud = !hud;
  if (mock.takeTelemetryToggle()) {
    telemetry = !telemetry;
    if (telemetry) sendHeader();
  }
}
}  // namespace

void loop() {
  uint32_t now = millis();
  while (Serial.available()) handleKey((char)Serial.read(), now);

  if ((int32_t)(now - nextTick) < 0) return;
  if (now - nextTick > 100) nextTick = now;  // fell far behind (e.g. serial burst): resync
  uint32_t t = nextTick;                      // logic runs on the grid, not on millis() jitter
  nextTick += TICK_MS;

  mock.tick(t);
  MusicEvent e;
  while (mock.pop(t, e)) {
    director.onEvent(e, t);
    pet.event(e, t);
  }
  pet.tick(mock.features(t), t);
  if (++tickCount % TICKS_PER_FRAME == 0) frame(t, now);
  if (tickCount % 100 == 0) saveMemoryIfDue(t);   // checked once a second; saves rarely
  if (directing && director.summary(line, sizeof(line), pet, t)) Serial.println(line);
}
