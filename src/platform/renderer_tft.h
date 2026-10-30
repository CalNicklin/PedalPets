#pragma once
#include <TFT_eSPI.h>
#include "core/art_tables.h"
#include "core/doll.h"
#include "gen/pack.h"

struct HudInfo {
  const char* mood;
  float       energy;
  const char* reaction;  // nullptr when idle
  int         step;
};

class RendererTft {
 public:
  void begin();
#if PEDALPETS_DOLL
  // Paper doll: every part at its placement, back to front.
  void drawDoll(const DollPlacement* parts, const HudInfo* hud);
#else
  // Whole-frame clip art.
  void draw(uint16_t pose, Eye eye, const HudInfo* hud);  // hud == nullptr hides it
#endif

 private:
  void background();
  void finish(const HudInfo* hud);
  void blitPal4(const uint8_t* src, int w, int h, int x0, int y0);
  void drawEyes(int cx, int cy, Eye eye);

  TFT_eSPI    tft_;
  TFT_eSprite canvas_{&tft_};
  uint16_t    palette_[16] = {};  // byte-swapped for direct sprite-buffer writes
};
