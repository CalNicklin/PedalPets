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
#include "core/choreo.h"
#include "core/doll.h"
#include "core/mood.h"
#include "core/leaves.h"
#include "gen/doll_meta.h"
#include "gen/doll_moves.h"
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
MoodModel     moodModel;
Choreographer choreo(doll_gen::CHOREO, rng);
DollPlacement placements[doll_gen::PART_COUNT];
MarkPlacement markPlacements[CHOREO_MAX_MARKS];
LeafField       leaves;
PetMotionSensor motion;
char            line[1024];
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
  moodModel.reset(now);
  choreo.reset(moodModel.mood(), now);
  motion = PetMotionSensor();
#if PEDALPETS_SCENE
  leaves.scatter(rng, TELEMETRY_LEAVES, scene_gen::LEAF_COLOURS);
#endif
#else
  brain.reset(now);
  eyes.reset(now);
#endif
}

#if PEDALPETS_DOLL
// Logic tick for the paper doll: mood from the music, moves from the mood.
void dollTick(uint32_t t) {
  MusicEvent e;
  while (mock.pop(t, e)) {
    MoodChange c = moodModel.onEvent(e, t);
    if (c == MoodChange::Woke) choreo.onMoodChange(c, moodModel.mood(), t);  // waking eats the event
    else choreo.onEvent(e, moodModel.mood(), t);
  }
  MoodChange c = moodModel.tick(mock.features(t), t);
  if (c != MoodChange::None) choreo.onMoodChange(c, moodModel.mood(), t);
}

void dollFrame(uint32_t t, uint32_t now) {
  choreo.tick(moodModel.mood(), moodModel.energy(), t);
  composeDoll(doll_gen::DOLL, choreo.pose(), placements);
  int marks = placeMarks(doll_gen::CHOREO, choreo, doll_gen::DOLL, placements, markPlacements);
#if PEDALPETS_SCENE
  int fx, fy;                                   // the pet's feet, in screen pixels
  pivotOnCanvas(doll_gen::DOLL, placements[0], &fx, &fy);
  const DollPose& pose = choreo.pose();
  PetMotion m = motion.update(pose.ch[doll_gen::CH_X], pose.ch[doll_gen::CH_HOP], pose.ch[doll_gen::CH_FLAPL],
                              (160 - doll_gen::CANVAS_W) / 2 + fx, 128 - doll_gen::CANVAS_H + fy);
  leaves.step(rng, m);
  const LeafField* scene = &leaves;
  const float feetY = scene_gen::FEET_Y;
  auto leafSprite = [](int i) {
    const Leaf& l = leaves.leaf(i);
    return scene_gen::leafSprite(l.colour, leaves.rotation(i, scene_gen::LEAF_ROTATIONS), leaves.edgeOn(i));
  };
#else
  const LeafField* scene = nullptr;
  const float feetY = 0;
  auto leafSprite = [](int) { return -1; };
#endif
  int rx = choreo.reaction();
  HudInfo info = {MOOD_NAMES[(int)moodModel.mood()], moodModel.energy(),
                  rx >= 0 ? doll_gen::MOVE_NAMES[rx] : nullptr, 0};
  uint32_t start = micros();
  renderer.drawDoll(placements, markPlacements, marks, scene, hud ? &info : nullptr);
  if (telemetry) {
    dollTelemetryRow(line, sizeof(line), now, (int)moodModel.mood(), moodModel.energy(), info.reaction,
                     (long)(micros() - start), placements, doll_gen::PART_COUNT, markPlacements, marks, scene,
                     feetY, leafSprite);
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
