#pragma once
#include <stdint.h>

// Logic ticks and display frames share one grid so every pose is held for a
// whole number of frames (animators' "on twos/threes") — uneven holds read as
// stutter.
constexpr uint32_t TICK_MS         = 10;  // input, mood, performer, eyes
constexpr uint32_t TICKS_PER_FRAME = 3;
constexpr uint32_t FRAME_MS        = TICK_MS * TICKS_PER_FRAME;  // ~33 fps

// Round a duration to whole frames, at least one.
constexpr uint32_t toFrames(uint32_t ms) {
  return (ms + FRAME_MS / 2) / FRAME_MS > 0 ? (ms + FRAME_MS / 2) / FRAME_MS : 1;
}
