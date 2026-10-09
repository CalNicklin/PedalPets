#pragma once
#include <stdint.h>

// xorshift32 — small, deterministic per seed (tests pass fixed seeds).
class Rng {
 public:
  explicit Rng(uint32_t seed) : s_(seed ? seed : 0x9E3779B9u) {}
  uint32_t next() { s_ ^= s_ << 13; s_ ^= s_ >> 17; s_ ^= s_ << 5; return s_; }
  // Uniform in [lo, hi], inclusive.
  uint32_t range(uint32_t lo, uint32_t hi) { return hi <= lo ? lo : lo + next() % (hi - lo + 1); }
  // v ± pct (pct in 0..1).
  uint32_t jitter(uint32_t v, float pct) { uint32_t d = (uint32_t)(v * pct); return range(v - d, v + d); }
 private:
  uint32_t s_;
};
