#include "renderer_tft.h"
#include "platform/doll_pet.h"

namespace {
constexpr uint16_t PLAIN_BG = 0xDF3D;   // used when there's no scene
}  // namespace

void RendererTft::begin() {
  tft_.init();
  tft_.setRotation(1);
  tft_.fillScreen(PLAIN_BG);
  canvas_.setColorDepth(16);
  canvas_.createSprite(SCREEN_W, SCREEN_H);
  canvas_.setSwapBytes(true);
}

void RendererTft::swapPalette(const uint16_t* in, uint16_t* out) {
  for (int i = 0; i < 16; i++) out[i] = (in[i] >> 8) | (in[i] << 8);
}

void RendererTft::background(const Scene* scene) {
  if (scene && scene->backdrop) memcpy(canvas_.getPointer(), scene->backdrop, SCREEN_W * SCREEN_H * 2);
  else canvas_.fillSprite(PLAIN_BG);
}

void RendererTft::drawLeaves(const Scene& scene, const LeafField& leaves, bool front) {
  if (!scene.leafColours) return;
  if (leafPaletteFor_ != &scene) {
    swapPalette(scene.leafPalette, leafPalette_);
    leafPaletteFor_ = &scene;
  }
  for (int i = 0; i < leaves.count(); i++) {
    if (leaves.inFront(i, scene.feetY) != front) continue;
    const Leaf& l = leaves.leaf(i);
    int s = leafSprite(scene, l.colour, leaves.rotation(i, scene.leafRotations), leaves.edgeOn(i));
    int w = scene.leafSizes[s][0], h = scene.leafSizes[s][1];
    blitPal4(scene.leafPixels[s], w, h, (int)lroundf(l.x) - w / 2, (int)lroundf(l.y) - h + 1, false, leafPalette_);
  }
}

// 4-bit palette pixels straight into the sprite buffer; index 0 is transparent.
void RendererTft::blitPal4(const uint8_t* src, int w, int h, int x0, int y0, bool flip, const uint16_t* pal) {
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
    canvas_.setTextColor(TFT_BLACK, PLAIN_BG);
    canvas_.setCursor(2, 2);
    canvas_.printf("%s %.2f %s", hud->mood, hud->energy, hud->reaction ? hud->reaction : "");
    if (hud->thought) {
      canvas_.setCursor(2, 12);
      canvas_.print(hud->thought);
    }
  }
  canvas_.pushSprite(0, 0);
}

void RendererTft::drawDoll(const Character& c, const Scene* scene, const DollPlacement* parts,
                           const MarkPlacement* marks, int markCount, const LeafField* leaves,
                           const CritterView* crowd, int crowdCount, const HudInfo* hud) {
  if (paletteFor_ != &c) {
    swapPalette(c.palette, palette_);
    paletteFor_ = &c;
  }
  const int cx = (SCREEN_W - c.canvasW) / 2, cy = SCREEN_H - c.canvasH;   // canvas bottom-centred
  background(scene);
  if (scene && crowdCount) {                                 // the crowd, at the edges
    if (crowdPaletteFor_ != scene) {
      swapPalette(scene->crowdPalette, crowdPalette_);
      crowdPaletteFor_ = scene;
    }
    for (int i = 0; i < crowdCount; i++) {
      const CritterView& v = crowd[i];
      blitPal4(scene->crowdPixels[v.sprite], scene->crowdSizes[v.sprite][0], scene->crowdSizes[v.sprite][1], v.x,
               v.y, v.flip, crowdPalette_);
    }
  }
  if (scene && leaves) drawLeaves(*scene, *leaves, false);   // leaves behind the pet
  for (int i = 0; i < c.doll.partCount; i++) {
    const DollPlacement& p = parts[c.doll.drawOrder[i]];
    const DollImage& im = c.doll.images[p.image];
    blitPal4(c.pixels[p.image], im.w, im.h, cx + p.x, cy + p.y, p.flip, palette_);
  }
  if (scene && leaves) drawLeaves(*scene, *leaves, true);    // leaves in front of it
  for (int i = 0; i < markCount; i++) {                      // expression marks on top, never mirrored
    const MarkSize& sz = c.choreo.markSizes[marks[i].image];
    blitPal4(c.markPixels[marks[i].image], sz.w, sz.h, cx + marks[i].x, cy + marks[i].y, false, palette_);
  }
  finish(hud);
}
