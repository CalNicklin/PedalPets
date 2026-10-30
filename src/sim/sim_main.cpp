// Desktop simulator: runs the firmware's brain, performer, eyes and mock input
// in virtual time with the device loop's cadence (10 ms ticks, 33 ms frames)
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
#include "gen/pose_meta.h"
#include "platform/mock_input.h"

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

  Rng           rng(seed);
  Performer     performer(gen::ART, rng);
  Brain         brain(gen::ART, rng, performer);
  EyeController eyes(rng);
  MockInput     mock;
  mock.reset();
  brain.reset(0);
  eyes.reset(0);

  printf("t_ms,pose,eye,mood,energy,reaction,step,frame_us\n");
  uint32_t lastTick = 0, lastFrame = 0;
  for (uint32_t now = 0; now <= duration; now++) {
    for (int i = 0; i < nkeys; i++)
      if (keys[i].at == now) mock.key(keys[i].key, now);
    if (now - lastTick >= 10) {
      lastTick = now;
      mock.tick(now);
      MusicEvent e;
      while (mock.pop(now, e)) brain.onEvent(e, now);
      brain.tick(mock.features(now), now);
      eyes.tick(brain.mood(), performer.eyes(), now);
    }
    if (now - lastFrame >= 33) {
      lastFrame = now;
      printf("%u,%u,%d,%d,%.3f,%s,%d,\n", now, performer.pose(), (int)eyes.eye(), (int)brain.mood(),
             brain.energy(), performer.playing() ? gen::REACTION_IDS[performer.reaction()] : "-",
             performer.step());
    }
  }
  return 0;
}
