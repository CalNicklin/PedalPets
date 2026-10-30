#pragma once
#include <TFT_eSPI.h>
#include "core/doll.h"
#include "core/leaves.h"
#include "core/pack.h"

struct HudInfo {
  const char* mood;
  float       energy;
  const char* reaction;  // nullptr when idle
  const char* thought;
};

// A speech bubble: what to say, and the head's box on screen to put it by.
struct Bubble {
  const char* text;      // nullptr: nothing to say
  int         headX0, headY0, headX1, headY1;
  bool        facingLeft;
};

class RendererTft {
 public:
  void begin();
  // The scene's backdrop, its crowd and leaves, the character's parts back to
  // front, its expression marks and speech bubble on top. scene == nullptr draws
  // a plain background.
  void drawDoll(const Character& c, const Scene* scene, const DollPlacement* parts, const MarkPlacement* marks,
                int markCount, const LeafField* leaves, const struct CritterView* crowd, int crowdCount,
                const Bubble* bubble, const HudInfo* hud);

 private:
  void background(const Scene* scene);
  void finish(const HudInfo* hud);
  void blitPal4(const uint8_t* src, int w, int h, int x0, int y0, bool flip, const uint16_t* palette);
  void drawLeaves(const Scene& scene, const LeafField& leaves, bool front);
  void drawBubble(const Bubble& b);
  static void swapPalette(const uint16_t* in, uint16_t* out);

  TFT_eSPI         tft_;
  TFT_eSprite      canvas_{&tft_};
  const Character* paletteFor_ = nullptr;
  const Scene*     leafPaletteFor_ = nullptr;
  const Scene*     crowdPaletteFor_ = nullptr;
  uint16_t         crowdPalette_[16] = {};
  uint16_t         palette_[16] = {};      // byte-swapped for direct sprite-buffer writes
  uint16_t         leafPalette_[16] = {};
};
