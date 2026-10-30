#include "renderer_tft.h"

#if PEDALPETS_DOLL
#include "gen/doll_meta.h"
#include "gen/doll_moves.h"
#include "gen/doll_pixels.h"
namespace art = doll_gen;
#if __has_include("gen/scene.h")
#include "gen/scene.h"
#endif
#else
#include "gen/pose_meta.h"
#include "gen/pose_pixels.h"
namespace art = gen;
#endif

namespace {
constexpr int16_t  SCREEN_W = 160;
constexpr int16_t  SCREEN_H = 128;
constexpr int16_t  CANVAS_X = (SCREEN_W - art::CANVAS_W) / 2;  // centred, bottom-aligned
constexpr int16_t  CANVAS_Y = SCREEN_H - art::CANVAS_H;
constexpr uint16_t EYE = TFT_WHITE;
constexpr int16_t  SUN_X = SCREEN_W / 2, SUN_Y = 46, SUN_R = 36;
#if PEDALPETS_DOLL
constexpr bool HAS_SUN = true;
#define PEDALPETS_PAL4 1
#else
constexpr bool HAS_SUN = gen::HAS_SUN;
#define PEDALPETS_PAL4 PEDALPETS_PALETTED
#endif
}  // namespace

void RendererTft::begin() {
  tft_.init();
  tft_.setRotation(1);
  tft_.fillScreen(art::BG_COLOR);
  canvas_.setColorDepth(16);
  canvas_.createSprite(SCREEN_W, SCREEN_H);
  canvas_.setSwapBytes(true);
#if PEDALPETS_PAL4
  for (int i = 0; i < 16; i++) palette_[i] = (art::PALETTE[i] >> 8) | (art::PALETTE[i] << 8);
#endif
#if PEDALPETS_SCENE
  for (int i = 0; i < 16; i++)
    leafPalette_[i] = (scene_gen::LEAF_PALETTE[i] >> 8) | (scene_gen::LEAF_PALETTE[i] << 8);
#endif
}

void RendererTft::background() {
#if PEDALPETS_SCENE
  memcpy_P(canvas_.getPointer(), scene_gen::BACKDROP, sizeof(scene_gen::BACKDROP));
#else
  canvas_.fillSprite(art::BG_COLOR);
  if (HAS_SUN) canvas_.fillCircle(SUN_X, SUN_Y, SUN_R, art::SUN_COLOR);
#endif
}

void RendererTft::drawLeaves(const LeafField* leaves, bool front) {
#if PEDALPETS_SCENE
  if (!leaves) return;
  for (int i = 0; i < leaves->count(); i++) {
    if (leaves->inFront(i, scene_gen::FEET_Y) != front) continue;
    const Leaf& l = leaves->leaf(i);
    int s = scene_gen::leafSprite(l.colour, leaves->rotation(i, scene_gen::LEAF_ROTATIONS), leaves->edgeOn(i));
    int w = scene_gen::LEAF_SIZES[s][0], h = scene_gen::LEAF_SIZES[s][1];
    blitPal4(scene_gen::LEAF_PIXELS[s], w, h, (int)lroundf(l.x) - w / 2, (int)lroundf(l.y) - h + 1, false,
             leafPalette_);
  }
#else
  (void)leaves; (void)front;
#endif
}

// 4-bit palette pixels straight into the sprite buffer; index 0 is transparent.
void RendererTft::blitPal4(const uint8_t* src, int w, int h, int x0, int y0, bool flip,
                           const uint16_t* palette) {
  const uint16_t* pal = palette ? palette : palette_;
  uint16_t* buf = (uint16_t*)canvas_.getPointer();
  int stride = (w + 1) / 2;
  for (int r = 0; r < h; r++) {
    int sy = y0 + r;
    if (sy < 0 || sy >= SCREEN_H) continue;
    const uint8_t* row = src + r * stride;
    uint16_t* dst = buf + sy * SCREEN_W;
    for (int c = 0; c < w; c++) {
      uint8_t idx = (c & 1) ? (row[c >> 1] & 0x0F) : (row[c >> 1] >> 4);
      int sx = flip ? x0 + w - 1 - c : x0 + c;
      if (idx && sx >= 0 && sx < SCREEN_W) dst[sx] = pal[idx];
    }
  }
}

void RendererTft::finish(const HudInfo* hud) {
  if (hud) {
    canvas_.setTextFont(1);
    canvas_.setTextColor(TFT_BLACK, art::BG_COLOR);
    canvas_.setCursor(2, 2);
    canvas_.printf("%s %.2f", hud->mood, hud->energy);
    if (hud->reaction) {
      canvas_.setCursor(2, 12);
      canvas_.printf("%s #%d", hud->reaction, hud->step);
    }
  }
  canvas_.pushSprite(0, 0);
}

#if PEDALPETS_DOLL
void RendererTft::drawDoll(const DollPlacement* parts, const MarkPlacement* marks, int markCount,
                           const LeafField* leaves, const HudInfo* hud) {
  background();
  drawLeaves(leaves, false);                   // leaves behind the pet
  for (int i = 0; i < art::DOLL.partCount; i++) {
    const DollPlacement& p = parts[art::DOLL.drawOrder[i]];
    const DollImage& im = art::IMAGES[p.image];
    blitPal4(art::PIXELS[p.image], im.w, im.h, CANVAS_X + p.x, CANVAS_Y + p.y, p.flip);
  }
  drawLeaves(leaves, true);                    // leaves in front of it
  for (int i = 0; i < markCount; i++) {        // expression marks on top, never mirrored
    const MarkSize& sz = art::MARK_SIZES[marks[i].image];
    blitPal4(art::MARK_PIXELS[marks[i].image], sz.w, sz.h, CANVAS_X + marks[i].x, CANVAS_Y + marks[i].y);
  }
  finish(hud);
}
#else
void RendererTft::draw(uint16_t pose, Eye eye, const HudInfo* hud) {
  background();
  const PoseMeta& m = gen::POSES[pose];
#if PEDALPETS_PALETTED
  blitPal4(gen::POSE_PIXELS[pose], m.w, m.h, CANVAS_X + m.x, CANVAS_Y + m.y);
#else
  canvas_.pushImage(CANVAS_X + m.x, CANVAS_Y + m.y, m.w, m.h, (uint16_t*)gen::POSE_PIXELS[pose]);
#endif
  if (m.eyeX != EYES_BAKED) drawEyes(CANVAS_X + m.eyeX, CANVAS_Y + m.eyeY, eye);
  finish(hud);
}
#endif

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
