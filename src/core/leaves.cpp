#include "leaves.h"
#include <math.h>

namespace {
constexpr float PI = 3.14159265f;

float frand(Rng& rng, float lo, float hi) { return lo + (hi - lo) * (rng.next() % 1000) / 999.0f; }
float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
}  // namespace

PetMotion PetMotionSensor::update(float stageX, float hop, float flap, float feetX, float feetY) {
  PetMotion m = {feetX, feetY, 0, 0, 0, feetX};
  if (started_) {
    m.feetVx = stageX - stageX_;
    if (hop > 0.5f) peak_ = fmaxf(peak_, hop);
    else if (hop_ > 0.5f) { m.landing = clampf(peak_ / 10, 0, 1); peak_ = 0; }
    m.gust = clampf(fabsf(flap - flap_) / 40, 0, 1);
  }
  started_ = true;
  stageX_ = stageX;
  hop_ = hop;
  flap_ = flap;
  return m;
}

void LeafField::add(float x, float depth, uint8_t colour) {
  if (count_ >= MAX_LEAVES) return;
  Leaf& l = leaves_[count_++];
  l = Leaf();
  l.x = x;
  l.depth = depth;
  l.colour = colour;
  l.y = restY(count_ - 1);
  l.resting = true;
}

void LeafField::scatter(Rng& rng, int count, uint8_t colours) {
  clear();
  for (int i = 0; i < count; i++) {
    add(frand(rng, cfg_.xMin + 4, cfg_.xMax - 4), frand(rng, 0, 1), (uint8_t)(rng.next() % colours));
    leaves_[i].angle = frand(rng, -0.25f, 0.25f);   // lying (nearly) flat
  }
}

float LeafField::restY(int i) const {
  return cfg_.groundTop + leaves_[i].depth * (cfg_.groundBottom - cfg_.groundTop);
}

uint8_t LeafField::rotation(int i, uint8_t steps) const {
  float a = fmodf(leaves_[i].angle, PI);
  if (a < 0) a += PI;
  return (uint8_t)((int)lroundf(a / (PI / steps)) % steps);
}

bool LeafField::edgeOn(int i) const {
  return !leaves_[i].resting && fabsf(sinf(leaves_[i].angle * 2)) > 0.75f;
}

void LeafField::kick(Rng& rng, Leaf& l, float vx, float vy) {
  l.vx = vx + frand(rng, -0.3f, 0.3f);
  l.vy = vy * frand(rng, 0.8f, 1.2f);
  l.spin = frand(rng, -0.4f, 0.4f);
  l.resting = false;
}

void LeafField::step(Rng& rng, const PetMotion& m) {
  for (int i = 0; i < count_; i++) {
    Leaf& l = leaves_[i];
    float ry = restY(i);
    float dx = l.x - m.feetX;
    float dir = dx >= 0 ? 1.0f : -1.0f;

    // Feet: only leaves on (or just above) the ground, on the feet's row.
    bool underfoot = fabsf(dx) < cfg_.kickRadius && fabsf(ry - m.feetY) <= cfg_.depthReach && l.y >= ry - 1;
    if (underfoot && (fabsf(m.feetVx) >= cfg_.minKickSpeed || m.landing > 0.1f)) {
      kick(rng, l, m.feetVx * 1.6f + dir * (0.4f + m.landing * 0.8f),
           -(0.8f + fabsf(m.feetVx) * 1.2f + m.landing * 1.6f));
    }

    // Wing beats push leaves away from the pet, and can lift them.
    float gd = l.x - m.gustX;
    if (m.gust > 0 && fabsf(gd) < cfg_.gustRadius) {
      float push = m.gust * (1 - fabsf(gd) / cfg_.gustRadius);
      l.vx += (gd >= 0 ? 1 : -1) * push * 0.5f;
      if (l.resting && push > 0.4f) kick(rng, l, l.vx, -push * 1.2f);
      else if (l.resting && fabsf(l.vx) > 0.05f) l.resting = false;   // slides along the ground
    }

    if (l.resting) continue;
    l.vy += cfg_.gravity;
    if (l.vy > cfg_.maxFall) l.vy = cfg_.maxFall;            // leaves flutter down
    if (l.vy > 0) l.vx += cosf(l.angle) * 0.04f;             // ... rocking side to side
    l.vx *= cfg_.drag;
    l.x += l.vx;
    l.y += l.vy;
    l.angle += l.spin;
    l.spin *= 0.97f;
    if (l.x < cfg_.xMin) { l.x = cfg_.xMin; l.vx = fabsf(l.vx) * 0.5f; }
    if (l.x > cfg_.xMax) { l.x = cfg_.xMax; l.vx = -fabsf(l.vx) * 0.5f; }
    if (l.y >= ry) {                                          // on the ground: slide to a stop
      l.y = ry;
      l.vy = 0;
      l.vx *= cfg_.friction;
      l.spin *= 0.2f;
      if (fabsf(l.vx) < 0.08f) {
        l.vx = 0;
        l.resting = true;
        l.angle = frand(rng, -0.25f, 0.25f);             // settles lying flat
      }
    }
  }
}
