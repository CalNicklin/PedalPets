#include <unity.h>
#include "core/beat.h"

void setUp() {}
void tearDown() {}

static BeatClock clock;
static uint32_t t;
static int beats;

// Advance in 10 ms ticks, playing a note every `every` ms (0 = silence); counts beats.
static void play(uint32_t ms, uint32_t every, uint32_t offset = 0) {
  for (uint32_t i = 0; i < ms; i += 10) {
    t += 10;
    if (every && (t + offset) % every == 0) clock.onOnset(t);
    if (clock.tick(t)) beats++;
  }
}

void test_locks_onto_a_steady_tempo_and_its_phase() {
  clock.reset(0, 560);
  t = 0; beats = 0;
  play(8000, 500, 130);                        // notes every 500 ms, off the clock's first guess
  TEST_ASSERT_INT_WITHIN(15, 500, (int)clock.periodMs());
  TEST_ASSERT_TRUE(clock.confidence() > 0.7f);
  // the next note lands on a beat: the phase is near 0 (or 1) right then
  while ((t + 130) % 500 != 0) { t += 10; clock.tick(t); }
  float ph = clock.phase(t);
  TEST_ASSERT_TRUE(ph < 0.12f || ph > 0.88f);
}

void test_fast_notes_count_as_subdivisions() {
  clock.reset(0, 560);
  t = 0; beats = 0;
  play(8000, 250);                             // eighth notes at 120 bpm: the beat is 500 ms
  TEST_ASSERT_INT_WITHIN(20, 500, (int)clock.periodMs());
}

void test_keeps_time_through_a_pause_and_falls_back_to_its_own() {
  clock.reset(0, 560);
  t = 0; beats = 0;
  play(6000, 500);
  beats = 0;
  play(5000, 0);                               // silence: it keeps going at the same tempo
  TEST_ASSERT_INT_WITHIN(1, 10, beats);
  TEST_ASSERT_TRUE(clock.confidence() < 0.5f); // but is less sure of itself
}

void test_ignores_stray_notes() {
  clock.reset(0, 560);
  t = 0; beats = 0;
  play(6000, 500);
  clock.onOnset(t + 170);                      // one off-beat note
  play(2000, 500);
  TEST_ASSERT_INT_WITHIN(15, 500, (int)clock.periodMs());
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_locks_onto_a_steady_tempo_and_its_phase);
  RUN_TEST(test_fast_notes_count_as_subdivisions);
  RUN_TEST(test_keeps_time_through_a_pause_and_falls_back_to_its_own);
  RUN_TEST(test_ignores_stray_notes);
  return UNITY_END();
}
