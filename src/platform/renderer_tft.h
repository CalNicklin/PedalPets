#pragma once
#include <TFT_eSPI.h>
#include "core/art_tables.h"

struct HudInfo {
  const char* mood;
  float       energy;
  const char* reaction;  // nullptr when idle
  int         step;
};

class RendererTft {
 public:
  void begin();
  void draw(uint16_t pose, Eye eye, const HudInfo* hud);  // hud == nullptr hides it

 private:
  void drawEyes(int cx, int cy, Eye eye);
  void blitPose(uint16_t pose, int16_t x, int16_t y);

  TFT_eSPI    tft_;
  TFT_eSprite canvas_{&tft_};
  uint16_t    palette_[16] = {};  // byte-swapped for direct sprite-buffer writes
};
