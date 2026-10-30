#pragma once
#include <stdint.h>

// BeatClock: the pulse the pet dances to. It follows the notes you play
// (onOnset) like a drummer following a band: notes near where it expects a
// beat pull its phase and tempo in; fast notes count as subdivisions; stray
// ones are ignored. Between notes it keeps time, so the groove carries on.
// Hardware-free; live audio onsets or mock picks both feed it.

struct BeatConfig {
  uint32_t minPeriodMs = 360, maxPeriodMs = 900;   // ~67..167 bpm (the beat a body dances to)
  float    window      = 0.3f;    // a note within this share of a period of a beat counts
  float    phaseGain   = 0.35f;   // how hard a near note pulls the phase
  float    periodGain  = 0.12f;   // ... and the tempo
  float    trust       = 0.25f;   // confidence moves this far towards each note's verdict
  uint32_t fadeMs      = 2500;    // with no notes, confidence fades over this long
};

class BeatClock {
 public:
  explicit BeatClock(const BeatConfig& cfg = BeatConfig()) : cfg_(cfg) {}

  void  reset(uint32_t now, uint32_t periodMs);
  void  onOnset(uint32_t now);
  bool  tick(uint32_t now);                  // true on the tick a beat falls
  void  setTempo(uint32_t periodMs);         // with no confident lock: the mood's own tempo

  float    phase(uint32_t now) const;        // 0 on the beat .. 1 just before the next
  uint32_t beat() const { return count_; }   // beats so far
  float    periodMs() const { return period_; }
  float    confidence() const { return confidence_; }

 private:
  float fold(float ioi) const;               // an interval brought into the dancing range

  BeatConfig cfg_;
  float      period_ = 560, confidence_ = 0;
  float      lastBeat_ = 0, nextBeat_ = 560;
  uint32_t   count_ = 0, lastOnset_ = 0, lastTick_ = 0;
  bool       heard_ = false;
};
