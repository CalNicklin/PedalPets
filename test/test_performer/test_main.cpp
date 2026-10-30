#include <unity.h>
#include "core/performer.h"
#include "../fixture_art.h"

static Rng rng(1);
static Performer* p = nullptr;
static uint32_t t;

void setUp() {
  rng = Rng(1);
  delete p;
  p = new Performer(FX_ART, rng);
  t = 0;
  p->reset(Mood::Curious, t);
}
void tearDown() {}

static void run(Mood m, uint32_t ms, float energy = 0.0f) {
  for (uint32_t i = 0; i < ms; i += 10) { t += 10; p->tick(m, energy, t); }
}



// --- reactions ---------------------------------------------------------------

void test_reaction_plays_steps_then_returns_to_idle() {
  p->start(FX_BIGHIT, Trigger::BigHit, t);
  TEST_ASSERT_TRUE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(7, p->pose());
  TEST_ASSERT_EQUAL_INT((int)Eye::Wide, (int)p->eyes());
  run(Mood::Curious, 90);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());
  TEST_ASSERT_EQUAL_INT((int)Eye::Auto, (int)p->eyes());
  TEST_ASSERT_EQUAL_UINT8(1, p->step());
  run(Mood::Curious, 390);
  TEST_ASSERT_FALSE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());  // Curious idle, pose 0
}

void test_until_holds_until_event() {
  p->start(FX_SUSTAIN, Trigger::Sustain, t);
  run(Mood::Curious, 100);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());
  run(Mood::Curious, 500);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());  // still waiting
  p->onEvent(EventType::SustainEnd);
  run(Mood::Curious, 10);
  TEST_ASSERT_EQUAL_UINT16(9, p->pose());
}

void test_until_cap_expires_and_continues() {
  p->start(FX_SUSTAIN, Trigger::Sustain, t);
  run(Mood::Curious, 100);
  run(Mood::Curious, 1000);  // untilMax
  TEST_ASSERT_TRUE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(9, p->pose());
}

void test_until_event_before_step_plays_min_hold() {
  p->start(FX_SUSTAIN, Trigger::Sustain, t);
  p->onEvent(EventType::SustainEnd);  // arrives during step 0
  run(Mood::Curious, 100);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());
  run(Mood::Curious, 210);
  TEST_ASSERT_EQUAL_UINT16(9, p->pose());
}

void test_pose_current_freezes_previous_pose() {
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());
  p->start(FX_CUT, Trigger::Cut, t);
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());
  run(Mood::Curious, 300);
  TEST_ASSERT_EQUAL_UINT16(9, p->pose());
}

void test_random_hold_within_range() {
  for (uint32_t seed = 1; seed <= 20; seed++) {
    rng = Rng(seed);
    uint32_t start = t;
    p->start(FX_SWELL, Trigger::Swell, t);
    while (p->playing() && t - start < 1000) run(Mood::Curious, 10);
    uint32_t took = t - start;
    TEST_ASSERT_TRUE_MESSAGE(took >= 90 && took <= 300, "hold outside [100,300] rounded to frames");
    TEST_ASSERT_EQUAL_UINT32_MESSAGE(0, took % FRAME_MS, "hold is not a whole number of frames");
  }
}

// --- interrupts --------------------------------------------------------------

void test_interrupt_guard_120ms_from_reaction_start() {
  p->start(FX_SUSTAIN, Trigger::Sustain, t);
  TEST_ASSERT_FALSE(p->canInterrupt(Trigger::BigHit, t));
  run(Mood::Curious, 110);
  TEST_ASSERT_FALSE(p->canInterrupt(Trigger::BigHit, t));
  run(Mood::Curious, 10);
  TEST_ASSERT_TRUE(p->canInterrupt(Trigger::BigHit, t));
}

void test_equal_or_lower_priority_cannot_interrupt() {
  p->start(FX_CUT, Trigger::Cut, t);
  run(Mood::Curious, 200);
  TEST_ASSERT_FALSE(p->canInterrupt(Trigger::Flurry, t));
  TEST_ASSERT_FALSE(p->canInterrupt(Trigger::Cut, t));
}

void test_wake_uninterruptible_driftoff_always_interruptible() {
  p->start(FX_WAKE, Trigger::Wake, t);
  run(Mood::Curious, 300);
  TEST_ASSERT_FALSE(p->canInterrupt(Trigger::BigHit, t));
  p->start(FX_DRIFTOFF, Trigger::DriftOff, t);
  TEST_ASSERT_TRUE(p->canInterrupt(Trigger::Sustain, t));
}

void test_idle_can_always_be_interrupted() {
  TEST_ASSERT_TRUE(p->canInterrupt(Trigger::DriftOff, t));
}

void test_extend_restarts_current_step_hold() {
  p->start(FX_FLURRY, Trigger::Flurry, t);
  run(Mood::Curious, 200);
  p->extend(t);
  run(Mood::Curious, 200);
  TEST_ASSERT_TRUE(p->playing());
  run(Mood::Curious, 100);
  TEST_ASSERT_FALSE(p->playing());
}

// --- idles ---------------------------------------------------------------

// Times (ms after t0) at which the pose changes while idling.
static int changeTimes(Mood m, uint32_t ms, float energy, uint32_t* out, int max) {
  int n = 0;
  uint32_t t0 = t;
  for (uint32_t i = 0; i < ms; i += 10) {
    uint16_t before = p->pose();
    t += 10;
    p->tick(m, energy, t);
    if (p->pose() != before && n < max) out[n++] = t - t0;
  }
  return n;
}

void test_idle_cycles_at_its_period() {
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());
  run(Mood::Curious, 200);
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());
  run(Mood::Curious, 10);   // 210 ms period
  TEST_ASSERT_EQUAL_UINT16(2, p->pose());
  run(Mood::Curious, 210);
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());  // loops
}

void test_idle_holds_are_uniform_whole_frames() {
  p->reset(Mood::IntoIt, t);
  uint32_t at[32];
  int n = changeTimes(Mood::IntoIt, 900, 0.0f, at, 32);
  TEST_ASSERT_EQUAL_INT(10, n);
  for (int i = 1; i < n; i++) TEST_ASSERT_EQUAL_UINT32(90, at[i] - at[i - 1]);
}

void test_energy_speeds_up_in_whole_frames() {
  p->reset(Mood::IntoIt, t);
  uint32_t at[64];
  int n = changeTimes(Mood::IntoIt, 1200, 1.0f, at, 64);  // 90 / 1.6 → 2 frames
  TEST_ASSERT_TRUE(n >= 18);
  for (int i = 2; i < n; i++) TEST_ASSERT_EQUAL_UINT32(60, at[i] - at[i - 1]);
}

void test_speed_has_hysteresis() {
  p->reset(Mood::IntoIt, t);
  uint32_t at[64];
  // 3 frames at rest; energy 0.34 → 2.48 frames: too close to switch.
  int n = changeTimes(Mood::IntoIt, 900, 0.34f, at, 64);
  for (int i = 2; i < n; i++) TEST_ASSERT_EQUAL_UINT32(90, at[i] - at[i - 1]);
  // energy 0.6 → 2.17 frames: switch to 2. Then 0.30 → 2.53: stay at 2.
  changeTimes(Mood::IntoIt, 300, 0.6f, at, 64);
  n = changeTimes(Mood::IntoIt, 900, 0.30f, at, 64);
  for (int i = 1; i < n; i++) TEST_ASSERT_EQUAL_UINT32(60, at[i] - at[i - 1]);
}

void test_mood_change_waits_for_loop_end() {
  run(Mood::IntoIt, 10);
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());  // current pose not finished
  run(Mood::IntoIt, 200);
  TEST_ASSERT_EQUAL_UINT16(2, p->pose());  // loop carries on to its last pose
  run(Mood::IntoIt, 210);
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());  // then hands over to IntoIt's pose 0
}

// --- reaction loop sections -----------------------------------------------------

// Poses shown, one entry per change, until the reaction ends (or maxMs).
static int playPoses(uint16_t* out, int max, uint32_t maxMs, uint32_t extendAt = 0,
                     uint32_t eventAt = 0) {
  int n = 0;
  uint32_t t0 = t;
  out[n++] = p->pose();
  while (p->playing() && t - t0 < maxMs && n < max) {
    t += 10;
    if (extendAt && t - t0 == extendAt) p->extend(t);
    if (eventAt && t - t0 == eventAt) p->onEvent(EventType::SustainEnd);
    uint16_t before = p->pose();
    p->tick(Mood::Curious, 0.0f, t);
    if (p->playing() && p->pose() != before) out[n++] = p->pose();
  }
  return n;
}

void test_loop_section_plays_once_without_extend() {
  p->start(FX_LOOP_EXTEND, Trigger::Flurry, t);
  uint16_t seen[16];
  int n = playPoses(seen, 16, 2000);
  uint16_t want[] = {1, 2, 3, 4};
  TEST_ASSERT_EQUAL_INT(4, n);
  TEST_ASSERT_EQUAL_UINT16_ARRAY(want, seen, 4);
}

void test_extend_repeats_loop_section() {
  p->start(FX_LOOP_EXTEND, Trigger::Flurry, t);
  uint16_t seen[16];
  int n = playPoses(seen, 16, 2000, /*extendAt=*/100);
  uint16_t want[] = {1, 2, 3, 2, 3, 4};
  TEST_ASSERT_EQUAL_INT(6, n);
  TEST_ASSERT_EQUAL_UINT16_ARRAY(want, seen, 6);
}

void test_loop_until_event_then_outro() {
  p->start(FX_LOOP_UNTIL, Trigger::Sustain, t);
  uint16_t seen[32];
  int n = playPoses(seen, 32, 3000, 0, /*eventAt=*/500);
  // 1 (90) then 2,3 looping every 180 ms; event at 500 ms lets the current pass finish.
  uint16_t want[] = {1, 2, 3, 2, 3, 2, 3, 4};
  TEST_ASSERT_EQUAL_INT(8, n);
  TEST_ASSERT_EQUAL_UINT16_ARRAY(want, seen, 8);
}

void test_matched_entry_starts_at_closest_step() {
  p->reset(Mood::IntoIt, t);                 // pose 3
  p->start(FX_ENTRY, Trigger::Swell, t);
  TEST_ASSERT_EQUAL_UINT8(0, p->step());     // pose 3 has no better entry
  run(Mood::IntoIt, 500);
  p->reset(Mood::IntoIt, t);
  run(Mood::IntoIt, 90);                     // IntoIt cycle moves on to pose 4
  TEST_ASSERT_EQUAL_UINT16(4, p->pose());
  p->start(FX_ENTRY, Trigger::Swell, t);
  TEST_ASSERT_EQUAL_UINT8(2, p->step());     // joins the reaction at its matching step
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
}

void test_loop_until_caps_at_max() {
  p->start(FX_LOOP_UNTIL, Trigger::Sustain, t);
  uint16_t seen[64];
  int n = playPoses(seen, 64, 5000);   // no event: stops looping after 1000 ms
  TEST_ASSERT_EQUAL_UINT16(4, seen[n - 1]);
  TEST_ASSERT_TRUE(n <= 2 + 2 * 6);
}

void test_reaction_ends_into_new_moods_idle_at_pose_0() {
  run(Mood::Curious, 210);
  TEST_ASSERT_EQUAL_UINT16(2, p->pose());
  p->start(FX_BIGHIT, Trigger::BigHit, t);
  run(Mood::Hyped, 480);   // mood changed mid-reaction
  TEST_ASSERT_FALSE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(5, p->pose());
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_reaction_plays_steps_then_returns_to_idle);
  RUN_TEST(test_until_holds_until_event);
  RUN_TEST(test_until_cap_expires_and_continues);
  RUN_TEST(test_until_event_before_step_plays_min_hold);
  RUN_TEST(test_pose_current_freezes_previous_pose);
  RUN_TEST(test_random_hold_within_range);
  RUN_TEST(test_interrupt_guard_120ms_from_reaction_start);
  RUN_TEST(test_equal_or_lower_priority_cannot_interrupt);
  RUN_TEST(test_wake_uninterruptible_driftoff_always_interruptible);
  RUN_TEST(test_idle_can_always_be_interrupted);
  RUN_TEST(test_extend_restarts_current_step_hold);
  RUN_TEST(test_idle_cycles_at_its_period);
  RUN_TEST(test_idle_holds_are_uniform_whole_frames);
  RUN_TEST(test_energy_speeds_up_in_whole_frames);
  RUN_TEST(test_speed_has_hysteresis);
  RUN_TEST(test_mood_change_waits_for_loop_end);
  RUN_TEST(test_loop_section_plays_once_without_extend);
  RUN_TEST(test_extend_repeats_loop_section);
  RUN_TEST(test_loop_until_event_then_outro);
  RUN_TEST(test_loop_until_caps_at_max);
  RUN_TEST(test_matched_entry_starts_at_closest_step);
  RUN_TEST(test_reaction_ends_into_new_moods_idle_at_pose_0);
  return UNITY_END();
}
