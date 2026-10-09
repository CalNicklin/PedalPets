#include <unity.h>
#include "core/mood.h"

#define ASSERT_MOOD(expected) TEST_ASSERT_EQUAL_INT((int)(expected), (int)m.mood())

static MoodModel m;
static uint32_t t;

void setUp() { m = MoodModel(); t = 0; m.reset(t); }
void tearDown() {}

// Tick at 100 Hz for `ms` with a constant level.
static void run(float level, uint32_t ms) {
  for (uint32_t i = 0; i < ms; i += 10) { t += 10; m.tick({level, 0}, t); }
}
static MusicEvent ev(EventType type, float strength = 1.0f) { return {type, t, strength}; }
static void wake() { m.onEvent(ev(EventType::Pick), t); }

void test_starts_asleep_with_zero_energy() {
  ASSERT_MOOD(Mood::Asleep);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, m.energy());
}

void test_event_wakes_immediately_and_is_consumed() {
  TEST_ASSERT_EQUAL_INT((int)MoodChange::Woke, (int)m.onEvent(ev(EventType::BigHit), t));
  ASSERT_MOOD(Mood::Curious);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, m.energy());  // boost not applied
}

void test_level_does_not_wake() {
  run(1.0f, 5000);
  ASSERT_MOOD(Mood::Asleep);
}

void test_event_boosts_energy() {
  wake();
  m.onEvent(ev(EventType::BigHit), t);
  TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.2f, m.energy());
  m.onEvent(ev(EventType::Flurry), t);
  TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.3f, m.energy());
  m.onEvent(ev(EventType::Pick, 0.5f), t);
  TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.315f, m.energy());
  for (int i = 0; i < 10; i++) m.onEvent(ev(EventType::BigHit), t);
  TEST_ASSERT_EQUAL_FLOAT(1.0f, m.energy());
}

void test_energy_attacks_toward_level() {
  wake();
  run(0.5f, 1000);
  TEST_ASSERT_FLOAT_WITHIN(0.02f, 0.5f, m.energy());
}

void test_energy_decays_with_tau() {
  wake();
  run(1.0f, 500);
  float e0 = m.energy();
  run(0.0f, 8000);  // one time constant
  TEST_ASSERT_FLOAT_WITHIN(0.01f, e0 * 0.3679f, m.energy());
}

void test_dwell_then_hysteresis_into_it() {
  wake();
  run(0.5f, 1500);
  ASSERT_MOOD(Mood::Curious);   // energy high enough, but dwell not met
  run(0.5f, 600);
  ASSERT_MOOD(Mood::IntoIt);
  run(0.3f, 20000);
  ASSERT_MOOD(Mood::IntoIt);    // 0.3 is above the 0.25 down-threshold
  run(0.2f, 10000);
  ASSERT_MOOD(Mood::Curious);
}

void test_hyped_and_back() {
  wake();
  run(1.0f, 4500);
  ASSERT_MOOD(Mood::Hyped);
  run(0.6f, 10000);
  ASSERT_MOOD(Mood::Hyped);     // 0.6 is above the 0.55 down-threshold
  run(0.4f, 10000);
  ASSERT_MOOD(Mood::IntoIt);
}

void test_wind_down_passes_through_each_mood() {
  wake();
  run(1.0f, 4500);
  ASSERT_MOOD(Mood::Hyped);
  Mood seen[8]; int n = 0;
  uint32_t curiousAt = 0, asleepAt = 0;
  for (uint32_t i = 0; i < 60000 && m.mood() != Mood::Asleep; i += 10) {
    t += 10;
    MoodChange c = m.tick({0.0f, 0}, t);
    if (c == MoodChange::None) continue;
    seen[n++] = m.mood();
    if (m.mood() == Mood::Curious) curiousAt = t;
    if (c == MoodChange::FellAsleep) asleepAt = t;
  }
  TEST_ASSERT_EQUAL_INT(3, n);
  TEST_ASSERT_EQUAL_INT((int)Mood::IntoIt,  (int)seen[0]);
  TEST_ASSERT_EQUAL_INT((int)Mood::Curious, (int)seen[1]);
  TEST_ASSERT_EQUAL_INT((int)Mood::Asleep,  (int)seen[2]);
  TEST_ASSERT_TRUE(asleepAt - curiousAt >= 10000 && asleepAt - curiousAt <= 10010);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, m.energy());
}

void test_quiet_playing_keeps_it_awake() {
  wake();
  run(0.05f, 30000);   // above the 0.03 noise floor
  ASSERT_MOOD(Mood::Curious);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_starts_asleep_with_zero_energy);
  RUN_TEST(test_event_wakes_immediately_and_is_consumed);
  RUN_TEST(test_level_does_not_wake);
  RUN_TEST(test_event_boosts_energy);
  RUN_TEST(test_energy_attacks_toward_level);
  RUN_TEST(test_energy_decays_with_tau);
  RUN_TEST(test_dwell_then_hysteresis_into_it);
  RUN_TEST(test_hyped_and_back);
  RUN_TEST(test_wind_down_passes_through_each_mood);
  RUN_TEST(test_quiet_playing_keeps_it_awake);
  return UNITY_END();
}
