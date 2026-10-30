#include "renderer_tft.h"
#include "gen/pose_meta.h"
#include "gen/pose_pixels.h"

namespace {
constexpr int16_t  SCREEN_W = 160;
constexpr int16_t  SCREEN_H = 128;
constexpr int16_t  CANVAS_X = (SCREEN_W - gen::CANVAS_W) / 2;  // centred, bottom-aligned
constexpr int16_t  CANVAS_Y = SCREEN_H - gen::CANVAS_H;
constexpr uint16_t EYE = TFT_WHITE;
constexpr int16_t  SUN_X = SCREEN_W / 2, SUN_Y = 46, SUN_R = 36;
}  // namespace

void RendererTft::begin() {
  tft_.init();
  tft_.setRotation(1);
  tft_.fillScreen(gen::BG_COLOR);
  canvas_.setColorDepth(16);
  canvas_.createSprite(SCREEN_W, SCREEN_H);
  canvas_.setSwapBytes(true);
#if PEDALPETS_PALETTED
  for (int i = 0; i < 16; i++) palette_[i] = (gen::PALETTE[i] >> 8) | (gen::PALETTE[i] << 8);
#endif
}

#if PEDALPETS_PALETTED
// 4-bit palette pixels straight into the sprite buffer; index 0 is transparent.
void RendererTft::blitPose(uint16_t pose, int16_t x0, int16_t y0) {
  const PoseMeta& m = gen::POSES[pose];
  const uint8_t* src = gen::POSE_PIXELS[pose];
  uint16_t* buf = (uint16_t*)canvas_.getPointer();
  int stride = (m.w + 1) / 2;
  for (int r = 0; r < m.h; r++) {
    int sy = y0 + r;
    if (sy < 0 || sy >= SCREEN_H) continue;
    const uint8_t* row = src + r * stride;
    uint16_t* dst = buf + sy * SCREEN_W;
    for (int c = 0; c < m.w; c++) {
      uint8_t idx = (c & 1) ? (row[c >> 1] & 0x0F) : (row[c >> 1] >> 4);
      int sx = x0 + c;
      if (idx && sx >= 0 && sx < SCREEN_W) dst[sx] = palette_[idx];
    }
  }
}
#else
void RendererTft::blitPose(uint16_t pose, int16_t x0, int16_t y0) {
  const PoseMeta& m = gen::POSES[pose];
  canvas_.pushImage(x0, y0, m.w, m.h, (uint16_t*)gen::POSE_PIXELS[pose]);
}
#endif

void RendererTft::draw(uint16_t pose, Eye eye, const HudInfo* hud) {
  canvas_.fillSprite(gen::BG_COLOR);
  if (gen::HAS_SUN) canvas_.fillCircle(SUN_X, SUN_Y, SUN_R, gen::SUN_COLOR);
  const PoseMeta& m = gen::POSES[pose];
  blitPose(pose, CANVAS_X + m.x, CANVAS_Y + m.y);
  if (m.eyeX != EYES_BAKED) drawEyes(CANVAS_X + m.eyeX, CANVAS_Y + m.eyeY, eye);
  if (hud) {
    canvas_.setTextFont(1);
    canvas_.setTextColor(TFT_WHITE, gen::BG_COLOR);
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
