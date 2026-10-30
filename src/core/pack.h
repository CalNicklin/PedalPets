#pragma once
#include <stdint.h>
#include "choreo.h"
#include "doll.h"

// Packs: everything about how a pet *looks* (and what its moves are),
// separate from the mechanics that make it alive (mood, mind, choreographer,
// leaves). Generated into src/gen/chars/<name>/ and src/gen/scenes/<name>/;
// src/gen/packs.h lists them. See docs/superpowers/specs/2026-10-30-packs-and-skeleton-design.md.

struct Character {
  const char*         name;
  int16_t             canvasW, canvasH;     // the doll's canvas, bottom-centred on screen
  const DollTables&   doll;
  const Choreography& choreo;
  const char* const*  moveNames;
  const char* const*  channelNames;
  // Roles the engine needs: the head (gaze, the Mind's eye line) and the
  // channel whose swings gust the leaves (wings, arms; -1 = none).
  int8_t              headPart;
  int8_t              gustChannel;
  // Art: 4-bit images (index 0 transparent) and their RGB565 palette (entry 0 unused).
  const uint16_t*       palette;
  const uint8_t* const* pixels;
  const uint8_t* const* markPixels;
};

struct Scene {
  const char*            name;
  const uint16_t*        backdrop;          // 160x128 RGB565, byte-swapped for the sprite buffer
  float                  feetY;             // where the pet stands
  uint8_t                leafColours, leafRotations;   // 0 colours = no leaves
  const uint16_t*        leafPalette;
  const uint8_t* const*  leafPixels;        // [(colour * rotations + rotation) * 2 + edgeOn]
  const uint8_t        (*leafSizes)[2];
};

inline int leafSprite(const Scene& s, int colour, int rotation, bool edgeOn) {
  return (colour * s.leafRotations + rotation) * 2 + (edgeOn ? 1 : 0);
}
