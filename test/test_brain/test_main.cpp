#include <unity.h>
#include "core/brain.h"
#include "../fixture_art.h"

static Rng rng(7);
static Performer* perf = nullptr;
static Brain* brain = nullptr;
static uint32_t t;

void setUp() {
  delete brain;
  delete perf;
  rng = Rng(7);
  t = 0;
  perf = new Performer(FX_ART, rng);
  brain = new Brain(FX_ART, rng, *perf);
  brain->reset(t);
}
void tearDown() {}

static void run(float level, uint32_t ms) {
  for (uint32_t i = 0; i < ms; i += 10) { t += 10; brain->tick({level, 0}, t); }
}
static void send(EventType e, float strength = 1.0f) { brain->onEvent({e, t, strength}, t); }
static void wakeAndSettle() { send(EventType::Pick); run(0.0f, 600); }  // Wake is 500 ms

void test_event_while_asleep_plays_wake_only() {
  send(EventType::BigHit);
  TEST_ASSERT_EQUAL_INT((int)Mood::Curious, (int)brain->mood());
  TEST_ASSERT_EQUAL_INT(FX_WAKE, perf->reaction());
  TEST_ASSERT_EQUAL_FLOAT(0.0f, brain->energy());
}

void test_reaction_respects_mood_filter() {
  wakeAndSettle();
  send(EventType::BigHit);
  TEST_ASSERT_EQUAL_INT(FX_BIGHIT, perf->reaction());  // Hyped-only variant excluded
}

void test_variants_never_repeat_back_to_back() {
  wakeAndSettle();
  run(1.0f, 4500);
  TEST_ASSERT_EQUAL_INT((int)Mood::Hyped, (int)brain->mood());
  int prev = -1;
  for (int i = 0; i < 6; i++) {
    send(EventType::BigHit);
    int r = perf->reaction();
    TEST_ASSERT_TRUE(r == FX_BIGHIT || r == FX_BIGHIT_HYPED);
    TEST_ASSERT_NOT_EQUAL(prev, r);
    prev = r;
    run(1.0f, 1600);  // past cooldown and reaction end
  }
}

void test_cooldown_from_reaction_start() {
  wakeAndSettle();
  send(EventType::BigHit);
  run(0.0f, 600);
  TEST_ASSERT_FALSE(perf->playing());
  send(EventType::BigHit);           // 600 ms after start
  TEST_ASSERT_FALSE(perf->playing());
  run(0.0f, 900);                    // 1500 ms after start
  send(EventType::BigHit);
  TEST_ASSERT_EQUAL_INT(FX_BIGHIT, perf->reaction());
}

void test_lower_priority_is_dropped() {
  wakeAndSettle();
  send(EventType::BigHit);
  run(0.0f, 200);
  send(EventType::SustainStart);
  TEST_ASSERT_EQUAL_INT(FX_BIGHIT, perf->reaction());
}

void test_higher_priority_interrupts_after_guard_only() {
  wakeAndSettle();
  send(EventType::SustainStart);
  run(0.0f, 50);
  send(EventType::BigHit);
  TEST_ASSERT_EQUAL_INT(FX_SUSTAIN, perf->reaction());
  run(0.0f, 80);
  send(EventType::BigHit);
  TEST_ASSERT_EQUAL_INT(FX_BIGHIT, perf->reaction());
}

void test_repeat_flurry_extends_instead_of_restarting() {
  wakeAndSettle();
  send(EventType::Flurry);
  run(0.0f, 200);
  send(EventType::Flurry);
  run(0.0f, 250);
  TEST_ASSERT_EQUAL_INT(FX_FLURRY, perf->reaction());
  run(0.0f, 60);
  TEST_ASSERT_FALSE(perf->playing());
}

void test_until_event_reaches_performer() {
  wakeAndSettle();
  send(EventType::SustainStart);
  run(0.0f, 100);
  TEST_ASSERT_EQUAL_UINT16(8, perf->pose());
  send(EventType::SustainEnd);
  run(0.0f, 200);
  TEST_ASSERT_EQUAL_UINT16(9, perf->pose());
}

void test_drift_off_then_any_event_wakes() {
  wakeAndSettle();
  for (uint32_t i = 0; i < 40000 && brain->mood() != Mood::Asleep; i += 10) run(0.0f, 10);
  TEST_ASSERT_EQUAL_INT((int)Mood::Asleep, (int)brain->mood());
  TEST_ASSERT_EQUAL_INT(FX_DRIFTOFF, perf->reaction());
  send(EventType::Pick);
  TEST_ASSERT_EQUAL_INT(FX_WAKE, perf->reaction());
  TEST_ASSERT_EQUAL_INT((int)Mood::Curious, (int)brain->mood());
}

void test_reset_returns_to_sleep() {
  wakeAndSettle();
  brain->reset(t);
  TEST_ASSERT_EQUAL_INT((int)Mood::Asleep, (int)brain->mood());
  TEST_ASSERT_FALSE(perf->playing());
  TEST_ASSERT_EQUAL_UINT16(0, perf->pose());
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_event_while_asleep_plays_wake_only);
  RUN_TEST(test_reaction_respects_mood_filter);
  RUN_TEST(test_variants_never_repeat_back_to_back);
  RUN_TEST(test_cooldown_from_reaction_start);
  RUN_TEST(test_lower_priority_is_dropped);
  RUN_TEST(test_higher_priority_interrupts_after_guard_only);
  RUN_TEST(test_repeat_flurry_extends_instead_of_restarting);
  RUN_TEST(test_until_event_reaches_performer);
  RUN_TEST(test_drift_off_then_any_event_wakes);
  RUN_TEST(test_reset_returns_to_sleep);
  return UNITY_END();
}
