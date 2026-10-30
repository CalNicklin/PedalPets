#pragma once
#include <stdint.h>
#include "mood.h"
#include "music_event.h"
#include "rng.h"

// The crowd: little critters at the edges of the scene (mice in the bushes,
// ghosts behind the headstones) who come out as the music builds, bob along
// with the beats, cheer when it's hyped, duck at a big hit and peek out now
// and then while the pet sleeps. Hardware-free; the scene pack says where
// they are and what they look like.

enum class CritterPose : uint8_t { Hidden, Peek, Up, Cheer };

struct CrowdConfig {
  uint32_t staggerMaxMs = 900;     // critters come and go at their own pace
  uint32_t peekMs       = 500;     // coming out: eyes first
  uint32_t bobMs        = 150;     // a bob on the beat
  uint32_t duckMs       = 450;     // a big hit sends them back down for a moment
  uint32_t sleepPeekMinMs = 6000, sleepPeekMaxMs = 14000;
  uint32_t sleepPeekLenMs = 1600;
};

constexpr int CROWD_MAX = 6;

class Crowd {
 public:
  explicit Crowd(Rng& rng, const CrowdConfig& cfg = CrowdConfig()) : rng_(rng), cfg_(cfg) {}

  void reset(int count, uint32_t now);
  void onEvent(const MusicEvent& e, uint32_t now);
  void tick(Mood mood, float energy, uint32_t now);   // once per frame

  int         count() const { return count_; }
  CritterPose pose(int i) const { return c_[i].pose; }
  int         dip(int i) const { return c_[i].bobUntil && (int32_t)(now_ - c_[i].bobUntil) < 0 ? 1 : 0; }  // px down

 private:
  struct Critter {
    CritterPose pose = CritterPose::Hidden;
    float       shyness = 0.5f;       // 0..1: how much music it takes to bring it out
    uint32_t    changeAt = 0;         // when it acts on what it wants next
    uint32_t    outSince = 0;
    uint32_t    bobUntil = 0;
    bool        out = false;          // wants to be out
    uint32_t    peekUntil = 0;        // asleep: a quick peek
  };

  Rng&        rng_;
  CrowdConfig cfg_;
  Critter     c_[CROWD_MAX];
  int         count_ = 0;
  uint32_t    now_ = 0, duckUntil_ = 0, nextSleepPeek_ = 0;
  bool        hyped_ = false;
};
