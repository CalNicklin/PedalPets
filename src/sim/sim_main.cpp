// Desktop simulator: runs the firmware's brain, performer, eyes and mock input
// in virtual time with the device loop's cadence (10 ms ticks, render every 3rd)
// and writes one CSV row per rendered frame — the same columns as the
// device's `t` telemetry, so tools/render_timeline.py handles both.
//
//   usage: program "<key>@<ms> ..." <duration_ms> [seed]
//   e.g.   program "1@500" 90000 > sim.csv
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "core/brain.h"
#include "core/eyes.h"
#include "core/performer.h"
#include "core/timing.h"
#include "gen/pack.h"
#include "platform/mock_input.h"
#if PEDALPETS_DOLL
#include "core/choreo.h"
#include "core/doll.h"
#include "core/mood.h"
#include "core/leaves.h"
#include "gen/doll_meta.h"
#include "gen/doll_moves.h"
#include "platform/doll_telemetry.h"
#if __has_include("gen/scene.h")
#define PEDALPETS_SIM_SCENE 1
namespace scene_gen {   // the bits of gen/scene.h the simulator needs (no Arduino)
#include "gen/scene_consts.h"
}
#endif
#else
#include "gen/pose_meta.h"
#endif

namespace {
struct KeyAt { char key; uint32_t at; };

int parseKeys(const char* spec, KeyAt* out, int max) {
  int n = 0;
  const char* p = spec;
  while (*p && n < max) {
    while (*p == ' ') p++;
    if (!*p) break;
    out[n].key = *p++;
    out[n].at = (*p == '@') ? (uint32_t)strtoul(p + 1, (char**)&p, 10) : 0;
    n++;
  }
  return n;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: %s \"<key>@<ms> ...\" <duration_ms> [seed]\n", argv[0]);
    return 2;
  }
  KeyAt keys[64];
  int nkeys = parseKeys(argv[1], keys, 64);
  uint32_t duration = (uint32_t)strtoul(argv[2], nullptr, 10);
  uint32_t seed = argc > 3 ? (uint32_t)strtoul(argv[3], nullptr, 10) : 1;

  Rng       rng(seed);
  MockInput mock;
  mock.reset();
  uint32_t tickCount = 0;
#if PEDALPETS_DOLL
  MoodModel     mood;
  Choreographer choreo(doll_gen::CHOREO, rng);
  DollPlacement out[doll_gen::PART_COUNT];
  MarkPlacement marks[CHOREO_MAX_MARKS];
  LeafField       leaves;
  PetMotionSensor motion;
  static char     line[1024];
  mood.reset(0);
  choreo.reset(mood.mood(), 0);
#ifdef PEDALPETS_SIM_SCENE
  leaves.scatter(rng, TELEMETRY_LEAVES, scene_gen::LEAF_COLOURS);
#endif
  dollTelemetryHeader(line, sizeof(line), doll_gen::PART_COUNT);
  printf("%s\n", line);
#else
  Performer     performer(gen::ART, rng);
  Brain         brain(gen::ART, rng, performer);
  EyeController eyes(rng);
  brain.reset(0);
  eyes.reset(0);
  printf("t_ms,pose,eye,mood,energy,reaction,step,frame_us\n");
#endif
  for (uint32_t now = TICK_MS; now <= duration; now += TICK_MS) {
    for (int i = 0; i < nkeys; i++)
      if (keys[i].at > now - TICK_MS && keys[i].at <= now) mock.key(keys[i].key, now);
    mock.tick(now);
    MusicEvent e;
#if PEDALPETS_DOLL
    while (mock.pop(now, e)) {
      MoodChange c = mood.onEvent(e, now);
      if (c == MoodChange::Woke) choreo.onMoodChange(c, mood.mood(), now);
      else choreo.onEvent(e, mood.mood(), now);
    }
    MoodChange c = mood.tick(mock.features(now), now);
    if (c != MoodChange::None) choreo.onMoodChange(c, mood.mood(), now);
    if (++tickCount % TICKS_PER_FRAME == 0) {
      choreo.tick(mood.mood(), mood.energy(), now);
      composeDoll(doll_gen::DOLL, choreo.pose(), out);
      int rx = choreo.reaction();
      int nm = placeMarks(doll_gen::CHOREO, choreo, doll_gen::DOLL, out, marks);
      const LeafField* scene = nullptr;
      float feetY = 0;
#ifdef PEDALPETS_SIM_SCENE
      int fx, fy;
      pivotOnCanvas(doll_gen::DOLL, out[0], &fx, &fy);
      const DollPose& pose = choreo.pose();
      PetMotion m = motion.update(pose.ch[doll_gen::CH_X], pose.ch[doll_gen::CH_HOP], pose.ch[doll_gen::CH_FLAPL],
                                  (160 - doll_gen::CANVAS_W) / 2 + fx, 128 - doll_gen::CANVAS_H + fy);
      leaves.step(rng, m);
      scene = &leaves;
      feetY = scene_gen::FEET_Y;
#endif
      auto leafSprite = [&](int i) {
#ifdef PEDALPETS_SIM_SCENE
        const Leaf& l = leaves.leaf(i);
        return (l.colour * scene_gen::LEAF_ROTATIONS + leaves.rotation(i, scene_gen::LEAF_ROTATIONS)) * 2 +
               (leaves.edgeOn(i) ? 1 : 0);
#else
        (void)i;
        return -1;
#endif
      };
      dollTelemetryRow(line, sizeof(line), now, (int)mood.mood(), mood.energy(),
                       rx >= 0 ? doll_gen::MOVE_NAMES[rx] : nullptr, -1, out, doll_gen::PART_COUNT, marks, nm,
                       scene, feetY, leafSprite);
      printf("%s", line);
      if (getenv("PEDALPETS_CHANNELS")) {   // debug: raw channel values after the parts
        for (int c = 0; c < doll_gen::CHANNEL_COUNT; c++) printf(",%s=%.1f", doll_gen::CHANNEL_NAMES[c], choreo.pose().ch[c]);
      }
      printf("\n");
    }
#else
    while (mock.pop(now, e)) brain.onEvent(e, now);
    brain.tick(mock.features(now), now);
    eyes.tick(brain.mood(), performer.eyes(), now);
    if (++tickCount % TICKS_PER_FRAME == 0) {
      printf("%u,%u,%d,%d,%.3f,%s,%d,\n", now, performer.pose(), (int)eyes.eye(), (int)brain.mood(),
             brain.energy(), performer.playing() ? gen::REACTION_IDS[performer.reaction()] : "-",
             performer.step());
    }
#endif
  }
  return 0;
}
