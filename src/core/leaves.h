#pragma once
#include <stdint.h>
#include "rng.h"

// Fallen leaves on the ground strip. They lie still until the pet disturbs
// them: walking feet and hop landings kick them up, wing beats blow them away;
// then they tumble, flutter down and settle. Screen pixels, one step per frame.

// What the pet is doing near the ground this frame.
struct PetMotion {
  float feetX, feetY;   // where its feet are (screen)
  float feetVx;         // their horizontal speed (px/frame)
  float landing;        // 0..1 impact if it just landed from a hop
  float gust;           // 0..1 wing-beat strength
  float gustX;          // where the gust comes from
};

// Derives PetMotion from the pet's pose channels, frame to frame.
class PetMotionSensor {
 public:
  PetMotion update(float stageX, float hop, float flap, float feetX, float feetY);

 private:
  bool  started_ = false;
  float stageX_ = 0, hop_ = 0, flap_ = 0, peak_ = 0;
};

struct Leaf {
  float   x, y, vx, vy, angle, spin, depth;   // depth 0 = back of the strip, 1 = front
  uint8_t colour;
  bool    resting;
  int8_t  heldBy = -1;                      // hand holding it, or -1
};

// A hand in the world (screen px, px/frame): a moving one sweeps leaves; one
// closing next to a leaf picks it up, holds it while it grips, and throws it
// when it opens.
struct Hand { float x, y, vx, vy; bool grip, closing; };

struct LeafConfig {
  float groundTop = 115, groundBottom = 127;  // rest rows for depth 0..1
  float depthReach = 3;                       // feet only touch leaves this close to their row
  float kickRadius = 6;
  float minKickSpeed = 0.3f;
  float gravity = 0.16f, drag = 0.95f, maxFall = 0.9f, friction = 0.55f;
  float gustRadius = 36;
  float handReach = 5;                        // px: a moving hand sweeps leaves this close
  float grabReach = 6, grabDepth = 9;         // a closing hand grabs this close (x), allowing for the ground's depth rows
  float minSweepSpeed = 0.6f;
  float xMin = 1, xMax = 158;
};

constexpr int MAX_LEAVES = 16;

class LeafField {
 public:
  explicit LeafField(const LeafConfig& cfg = LeafConfig()) : cfg_(cfg) {}

  void clear() { count_ = 0; }
  void add(float x, float depth, uint8_t colour);
  void scatter(Rng& rng, int count, uint8_t colours);
  void step(Rng& rng, const PetMotion& m, const Hand* hands = nullptr, int handCount = 0);

  int         count() const { return count_; }
  const Leaf& leaf(int i) const { return leaves_[i]; }
  float       restY(int i) const;
  uint8_t     rotation(int i, uint8_t steps) const;   // in-plane angle bin
  bool        edgeOn(int i) const;                     // tumbling, seen edge-on
  bool        inFront(int i, float feetY) const { return leaves_[i].heldBy >= 0 || restY(i) > feetY; }

 private:
  void kick(Rng& rng, Leaf& l, float vx, float vy);
  bool holding(int hand) const;

  LeafConfig cfg_;
  Leaf       leaves_[MAX_LEAVES] = {};
  int        count_ = 0;
};
