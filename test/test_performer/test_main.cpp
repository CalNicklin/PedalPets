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

static void run(Mood m, uint32_t ms) {
  for (uint32_t i = 0; i < ms; i += 10) { t += 10; p->tick(m, t); }
}

// --- reactions ---------------------------------------------------------------

void test_reaction_plays_steps_then_returns_to_idle() {
  p->start(FX_BIGHIT, Trigger::BigHit, t);
  TEST_ASSERT_TRUE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(7, p->pose());
  TEST_ASSERT_EQUAL_INT((int)Eye::Wide, (int)p->eyes());
  run(Mood::Curious, 80);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());
  TEST_ASSERT_EQUAL_INT((int)Eye::Auto, (int)p->eyes());
  TEST_ASSERT_EQUAL_UINT8(1, p->step());
  run(Mood::Curious, 400);
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
  run(Mood::Curious, 200);
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
    TEST_ASSERT_TRUE_MESSAGE(took >= 100 && took <= 310, "hold outside [100,300]");
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

// --- idles -------------------------------------------------------------------

void test_curious_idle_advances_on_timer() {
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());
  run(Mood::Curious, 850);  // 700 ms ± 20 %
  TEST_ASSERT_EQUAL_UINT16(2, p->pose());
}

void test_mood_change_switches_idle_immediately() {
  run(Mood::IntoIt, 10);
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
}

void test_strong_pick_beat_steps_with_min_gap() {
  p->reset(Mood::IntoIt, t);
  t += 300; p->onPick(0.9f, t);
  TEST_ASSERT_EQUAL_UINT16(4, p->pose());
  t += 100; p->onPick(0.9f, t);
  TEST_ASSERT_EQUAL_UINT16(4, p->pose());  // < 250 ms since last step
  t += 200; p->onPick(0.9f, t);
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
}

void test_weak_picks_step_every_second_pick() {
  p->reset(Mood::IntoIt, t);
  t += 300; p->onPick(0.2f, t);
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
  t += 300; p->onPick(0.2f, t);
  TEST_ASSERT_EQUAL_UINT16(4, p->pose());
}

void test_picks_do_not_step_curious_idle() {
  t += 300; p->onPick(0.9f, t);
  TEST_ASSERT_EQUAL_UINT16(1, p->pose());
}

void test_beat_idle_falls_back_to_timer() {
  p->reset(Mood::IntoIt, t);
  run(Mood::IntoIt, 1490);
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
  run(Mood::IntoIt, 20);   // 1.5 s without a step
  TEST_ASSERT_EQUAL_UINT16(4, p->pose());
  run(Mood::IntoIt, 500);  // IntoIt timer period
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
}

void test_no_beat_step_during_reaction() {
  p->reset(Mood::IntoIt, t);
  p->start(FX_BIGHIT, Trigger::BigHit, t);
  run(Mood::IntoIt, 300);
  p->onPick(0.9f, t);
  TEST_ASSERT_EQUAL_UINT16(8, p->pose());
  run(Mood::IntoIt, 200);
  TEST_ASSERT_FALSE(p->playing());
  TEST_ASSERT_EQUAL_UINT16(3, p->pose());
}

void test_reaction_ends_into_new_moods_idle_at_pose_0() {
  run(Mood::Curious, 850);
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
  RUN_TEST(test_curious_idle_advances_on_timer);
  RUN_TEST(test_mood_change_switches_idle_immediately);
  RUN_TEST(test_strong_pick_beat_steps_with_min_gap);
  RUN_TEST(test_weak_picks_step_every_second_pick);
  RUN_TEST(test_picks_do_not_step_curious_idle);
  RUN_TEST(test_beat_idle_falls_back_to_timer);
  RUN_TEST(test_no_beat_step_during_reaction);
  RUN_TEST(test_reaction_ends_into_new_moods_idle_at_pose_0);
  return UNITY_END();
}
