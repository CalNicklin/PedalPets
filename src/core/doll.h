#pragma once
#include <stdint.h>

// Paper-doll character: body parts drawn as separate images, each picked from
// its own pose library and hung from its parent's attachment point.
// See docs/superpowers/specs/2026-10-30-paper-doll-design.md.

constexpr int DOLL_MAX_AXES     = 3;
constexpr int DOLL_MAX_PARTS    = 12;
constexpr int DOLL_MAX_CHANNELS = 24;

// An image axis: `count` values in axisValues[firstValue..] (quarter units, so
// axes can step in fractions), chosen by the sum of the channels in sourceMask
// (nearest value; ties pick the lower).
struct DollAxis { uint8_t count; uint16_t firstValue; uint32_t sourceMask; };

// One rendered part image: crop rect on the canvas, its pivot, and the first of
// its children's attachment points (positions in quarter pixels).
struct DollImage {
  uint8_t  x, y, w, h;
  int16_t  pivotX4, pivotY4;
  uint16_t firstAnchor;
};
struct DollAnchor { int16_t x4, y4; };

struct DollPart {
  int8_t   parent;        // -1 = stands on the ground
  uint8_t  anchorSlot;    // which of the parent's anchors this part hangs from
  uint8_t  axisCount;
  DollAxis axes[DOLL_MAX_AXES];
  uint16_t firstImage;    // images row-major over axes (first axis slowest)
  uint16_t imageCount;
};

struct DollTables {
  const DollPart*   parts;   uint8_t partCount;   // parents before children
  const uint8_t*    drawOrder;                     // back to front
  const DollImage*  images;
  const DollAnchor* anchors;
  const int16_t*    axisValues;
  uint8_t           channelCount;
  int8_t            hopChannel;                    // lifts the ground part (pixels)
  int8_t            xChannel;                      // moves the whole doll across the stage (pixels)
  int8_t            faceChannel;                   // < 0 mirrors the doll about its feet
};

struct DollPose { float ch[DOLL_MAX_CHANNELS]; };

// Where to draw one part: image index, canvas position of its crop, and
// whether to draw it mirrored left-right.
struct DollPlacement { uint16_t image; int16_t x, y; bool flip; };

// Fills out[partCount], indexed like tables.parts.
void composeDoll(const DollTables& t, const DollPose& p, DollPlacement* out);

// Canvas position of a placed part's pivot (e.g. the feet for the ground part).
void pivotOnCanvas(const DollTables& t, const DollPlacement& p, int* x, int* y);
