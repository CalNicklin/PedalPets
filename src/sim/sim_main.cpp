// Desktop simulator: runs the firmware's pet loop (platform/doll_pet.h) and
// mock input in virtual time with the device loop's cadence (10 ms ticks,
// render every 3rd) and writes one CSV row per rendered frame — the same
// columns as the device's `t` telemetry, so tools/doll_timeline.py handles both.
//
//   usage: program "<key>@<ms> ..." <duration_ms> [seed]
//   e.g.   program "1@500" 90000 > sim.csv
//   PET_CHAR=<name> / PET_SCENE=<name|none> pick the packs (default: the first of each);
//   PEDALPETS_CHANNELS=1 appends the raw channel values to each row.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "core/timing.h"
#include "gen/packs.h"
#include "platform/doll_pet.h"
#include "platform/doll_telemetry.h"
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

const Character* findCharacter(const char* name) {
  if (!name) return CHARACTERS[0];
  for (int i = 0; i < CHARACTER_COUNT; i++)
    if (!strcmp(CHARACTERS[i]->name, name)) return CHARACTERS[i];
  return nullptr;
}

const Scene* findScene(const char* name, bool* ok) {
  *ok = true;
  if (!name) return SCENE_COUNT ? SCENES[0] : nullptr;
  if (!strcmp(name, "none")) return nullptr;
  for (int i = 0; i < SCENE_COUNT; i++)
    if (!strcmp(SCENES[i]->name, name)) return SCENES[i];
  *ok = false;
  return nullptr;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: %s \"<key>@<ms> ...\" <duration_ms> [seed]\n", argv[0]);
    return 2;
  }
  const Character* character = findCharacter(getenv("PET_CHAR"));
  bool sceneOk;
  const Scene* scene = findScene(getenv("PET_SCENE"), &sceneOk);
  if (!character || !sceneOk) {
    fprintf(stderr, "unknown PET_CHAR or PET_SCENE\n");
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
  DollPet pet(*character, rng);
  pet.setScene(scene);
  pet.reset(0, TELEMETRY_LEAVES);
  const int parts = character->doll.partCount;
  static char line[1024];
  dollTelemetryHeader(line, sizeof(line), parts);
  printf("%s\n", line);
  auto sprite = [&](int i) {
    const Leaf& l = pet.leaves.leaf(i);
    return scene ? leafSprite(*scene, l.colour, pet.leaves.rotation(i, scene->leafRotations), pet.leaves.edgeOn(i))
                 : -1;
  };

  for (uint32_t now = TICK_MS; now <= duration; now += TICK_MS) {
    for (int i = 0; i < nkeys; i++)
      if (keys[i].at > now - TICK_MS && keys[i].at <= now) mock.key(keys[i].key, now);
    mock.tick(now);
    MusicEvent e;
    while (mock.pop(now, e)) pet.event(e, now);
    pet.tick(mock.features(now), now);
    if (++tickCount % TICKS_PER_FRAME != 0) continue;
    pet.frame(now);
    CritterView crowd[CROWD_MAX];
    int crowdCount = pet.critters(crowd);
    int rx = pet.choreo.reaction();
    dollTelemetryRow(line, sizeof(line), now, (int)pet.mood.mood(), pet.mood.energy(),
                     rx >= 0 ? character->moveNames[rx] : nullptr, pet.mind.thought(), -1, pet.parts, parts,
                     pet.marks, pet.markCount, scene && scene->leafColours ? &pet.leaves : nullptr,
                     scene ? scene->feetY : 0, sprite, crowd, crowdCount);
    printf("%s", line);
    if (getenv("PEDALPETS_CHANNELS")) {   // debug: raw channel values after the parts
      for (int c = 0; c < character->doll.channelCount; c++)
        printf(",%s=%.2f", character->channelNames[c], pet.choreo.pose().ch[c]);
      int nh;
      const Hand* hands = pet.hands(&nh);
      for (int k = 0; k < nh; k++) printf(",hand%dx=%.1f,hand%dy=%.1f,grip%d=%d", k, hands[k].x, k, hands[k].y, k, hands[k].grip);
      int held = 0;
      for (int i = 0; i < pet.leaves.count(); i++) held += pet.leaves.leaf(i).heldBy >= 0;
      printf(",held=%d", held);
      int hx, hy;
      pivotOnCanvas(character->doll, pet.parts[character->headPart], &hx, &hy);
      printf(",headx=%d", pet.canvasX() + hx);
    }
    printf("\n");
  }
  return 0;
}
