#include "doll.h"
#include <math.h>

namespace {
// Quarter pixels -> pixels, rounding half up (floor division).
int16_t roundQuarter(int32_t v4) {
  int32_t v = v4 + 2;
  return (int16_t)(v >= 0 ? v / 4 : -((-v + 3) / 4));
}

uint16_t nearest(const int16_t* vals, uint8_t count, float v) {
  uint16_t best = 0;
  float bestD = fabsf(vals[0] - v);
  for (uint16_t k = 1; k < count; k++) {
    float d = fabsf(vals[k] - v);
    if (d < bestD) { bestD = d; best = k; }
  }
  return best;
}
}  // namespace

void composeDoll(const DollTables& t, const DollPose& p, DollPlacement* out) {
  int32_t dx4[DOLL_MAX_PARTS], dy4[DOLL_MAX_PARTS];
  for (int i = 0; i < t.partCount; i++) {
    const DollPart& part = t.parts[i];
    uint16_t idx = 0;
    for (int a = 0; a < part.axisCount; a++) {
      const DollAxis& ax = part.axes[a];
      float v = 0;
      for (int c = 0; c < t.channelCount; c++)
        if (ax.sourceMask & (1u << c)) v += p.ch[c];
      idx = idx * ax.count + nearest(t.axisValues + ax.firstValue, ax.count, v * 4);
    }
    uint16_t img = part.firstImage + idx;
    const DollImage& im = t.images[img];

    int32_t ax4, ay4;   // where this part's pivot goes
    if (part.parent < 0) {
      const DollImage& rest = t.images[part.firstImage];
      float hop = t.hopChannel >= 0 ? p.ch[t.hopChannel] : 0.0f;
      float x = t.xChannel >= 0 ? p.ch[t.xChannel] : 0.0f;
      ax4 = rest.pivotX4 + (int32_t)lroundf(x * 4);
      ay4 = rest.pivotY4 - (int32_t)lroundf(hop * 4);
    } else {
      const DollImage& pim = t.images[out[part.parent].image];
      const DollAnchor& an = t.anchors[pim.firstAnchor + part.anchorSlot];
      ax4 = an.x4 + dx4[part.parent];
      ay4 = an.y4 + dy4[part.parent];
    }
    dx4[i] = ax4 - im.pivotX4;
    dy4[i] = ay4 - im.pivotY4;
    out[i] = {img, (int16_t)(im.x + roundQuarter(dx4[i])), (int16_t)(im.y + roundQuarter(dy4[i])), false};
  }

  // Facing the other way: mirror every part about the ground pivot (the feet).
  if (t.faceChannel >= 0 && p.ch[t.faceChannel] < 0) {
    const DollImage& g = t.images[out[0].image];
    int16_t mirror2 = roundQuarter(2 * (g.pivotX4 + dx4[0]));   // 2 x pivot, in pixels
    for (int i = 0; i < t.partCount; i++) {
      out[i].x = mirror2 - out[i].x - t.images[out[i].image].w;
      out[i].flip = true;
    }
  }
}
