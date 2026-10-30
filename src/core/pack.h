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
  // Hands (parts with tips) and the channel that closes each one (0.5..1.5 =
  // a fist: it grips); -1 = none. The moves the Mind asks for to walk up to
  // something and to reach for it, and how far ahead of the head that reach gets.
  int8_t              handParts[2];
  int8_t              gripChannels[2];
  int8_t              approachMove, reachMove;
  int8_t              reachPx;
  // Art: 4-bit images (index 0 transparent) and their RGB565 palette (entry 0 unused).
  const uint16_t*       palette;
  const uint8_t* const* pixels;
  const uint8_t* const* markPixels;
};

// A critter's spot in the scene: centre x, bottom y (screen px), and its kind.
struct CrowdSpot { int16_t x, y; uint8_t kind; };
constexpr int CROWD_FRAMES = 3;   // per kind: peek, up, cheer (facing left)

struct Scene {
  const char*            name;
  const uint16_t*        backdrop;          // 160x128 RGB565, byte-swapped for the sprite buffer
  float                  feetY;             // where the pet stands
  uint8_t                leafColours, leafRotations;   // 0 colours = no leaves
  const uint16_t*        leafPalette;
  const uint8_t* const*  leafPixels;        // [(colour * rotations + rotation) * 2 + edgeOn]
  const uint8_t        (*leafSizes)[2];
  const CrowdSpot*       crowd;             // the critters at the edges (crowdCount 0 = none)
  uint8_t                crowdCount;
  const uint16_t*        crowdPalette;
  const uint8_t* const*  crowdPixels;       // [kind * CROWD_FRAMES + frame]
  const uint8_t        (*crowdSizes)[2];
};

inline int leafSprite(const Scene& s, int colour, int rotation, bool edgeOn) {
  return (colour * s.leafRotations + rotation) * 2 + (edgeOn ? 1 : 0);
}
