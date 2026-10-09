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

  TFT_eSPI    tft_;
  TFT_eSprite canvas_{&tft_};
};
