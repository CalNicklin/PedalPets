#pragma once
// One CSV line per frame for a paper-doll pack, shared by the board ('t' key,
// lines prefixed "D,") and the simulator, so tools/doll_timeline.py can redraw
// exactly what was shown. The header is sent first (board: "H," prefix).
#include <stdio.h>
#include "core/choreo.h"
#include "core/doll.h"
#include "core/leaves.h"

constexpr int TELEMETRY_LEAVES = 12;

inline int dollTelemetryHeader(char* b, int n, int parts) {
  int k = snprintf(b, n, "t_ms,mood,energy,reaction,frame_us,flip");
  for (int i = 0; i < parts; i++) k += snprintf(b + k, n - k, ",p%d_img,p%d_x,p%d_y", i, i, i);
  for (int i = 0; i < CHOREO_MAX_MARKS; i++) k += snprintf(b + k, n - k, ",m%d_img,m%d_x,m%d_y", i, i, i);
  for (int i = 0; i < TELEMETRY_LEAVES; i++) k += snprintf(b + k, n - k, ",l%d_s,l%d_x,l%d_y,l%d_f", i, i, i, i);
  return k;
}

// leafSprite(i) -> sprite index (or -1 for no scene).
template <typename LeafSprite>
inline int dollTelemetryRow(char* b, int n, uint32_t t, int mood, float energy, const char* reaction,
                            long frameUs, const DollPlacement* parts, int partCount,
                            const MarkPlacement* marks, int markCount, const LeafField* leaves,
                            float feetY, LeafSprite leafSprite) {
  int k = snprintf(b, n, "%u,%d,%.3f,%s,", (unsigned)t, mood, energy, reaction ? reaction : "-");
  if (frameUs >= 0) k += snprintf(b + k, n - k, "%ld", frameUs);
  k += snprintf(b + k, n - k, ",%d", parts[0].flip ? 1 : 0);
  for (int i = 0; i < partCount; i++) k += snprintf(b + k, n - k, ",%u,%d,%d", parts[i].image, parts[i].x, parts[i].y);
  for (int i = 0; i < CHOREO_MAX_MARKS; i++)
    k += snprintf(b + k, n - k, ",%d,%d,%d", i < markCount ? marks[i].image : -1, i < markCount ? marks[i].x : 0,
                  i < markCount ? marks[i].y : 0);
  for (int i = 0; i < TELEMETRY_LEAVES; i++) {
    if (leaves && i < leaves->count()) {
      const Leaf& l = leaves->leaf(i);
      k += snprintf(b + k, n - k, ",%d,%d,%d,%d", leafSprite(i), (int)(l.x + 0.5f), (int)(l.y + 0.5f),
                    leaves->inFront(i, feetY) ? 1 : 0);
    } else {
      k += snprintf(b + k, n - k, ",-1,0,0,0");
    }
  }
  return k;
}
