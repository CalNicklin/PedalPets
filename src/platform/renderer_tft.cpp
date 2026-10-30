#include "renderer_tft.h"
#include "gen/pose_meta.h"
#include "gen/pose_pixels.h"

namespace {
constexpr int16_t  SCREEN_W = 160;
constexpr int16_t  SCREEN_H = 128;
constexpr int16_t  CANVAS_X = (SCREEN_W - gen::CANVAS_W) / 2;  // centred, bottom-aligned
constexpr int16_t  CANVAS_Y = SCREEN_H - gen::CANVAS_H;
// Black until the real art arrives with its off-white + sun background (sub-project 2).
constexpr uint16_t BG  = TFT_BLACK;
constexpr uint16_t EYE = TFT_WHITE;
}  // namespace

void RendererTft::begin() {
  tft_.init();
  tft_.setRotation(1);
  tft_.fillScreen(BG);
  canvas_.setColorDepth(16);
  canvas_.createSprite(SCREEN_W, SCREEN_H);
  canvas_.setSwapBytes(true);
}

void RendererTft::draw(uint16_t pose, Eye eye, const HudInfo* hud) {
  canvas_.fillSprite(BG);
  const PoseMeta& m = gen::POSES[pose];
  canvas_.pushImage(CANVAS_X + m.x, CANVAS_Y + m.y, m.w, m.h, (uint16_t*)gen::POSE_PIXELS[pose]);
  if (m.eyeX != EYES_BAKED) drawEyes(CANVAS_X + m.eyeX, CANVAS_Y + m.eyeY, eye);
  if (hud) {
    canvas_.setTextFont(1);
    canvas_.setTextColor(TFT_WHITE, BG);
    canvas_.setCursor(2, 2);
    canvas_.printf("%s %.2f", hud->mood, hud->energy);
    if (hud->reaction) {
      canvas_.setCursor(2, 12);
      canvas_.printf("%s #%d", hud->reaction, hud->step);
    }
  }
  canvas_.pushSprite(0, 0);
}

// Placeholder primitives: two dots 8 px apart. Real eye sprites arrive in sub-project 2.
void RendererTft::drawEyes(int cx, int cy, Eye eye) {
  int dx = eye == Eye::LookL ? -2 : eye == Eye::LookR ? 2 : 0;
  for (int side = -1; side <= 1; side += 2) {
    int x = cx + side * 4 + dx;
    switch (eye) {
      case Eye::Blink:
        canvas_.drawFastHLine(x - 1, cy, 3, EYE);
        break;
      case Eye::HappyClosed:
        canvas_.drawLine(x - 1, cy, x, cy - 1, EYE);
        canvas_.drawLine(x, cy - 1, x + 1, cy, EYE);
        break;
      case Eye::Wide:
        canvas_.fillRect(x - 2, cy - 2, 4, 4, EYE);
        break;
      default:
        canvas_.fillRect(x - 1, cy - 1, 3, 3, EYE);
        break;
    }
  }
}
