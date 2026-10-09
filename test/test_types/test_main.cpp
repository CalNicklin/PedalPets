#include <unity.h>
#include "core/art_tables.h"
#include "core/rng.h"

void setUp() {}
void tearDown() {}

void test_rng_is_deterministic_per_seed() {
  Rng a(42), b(42), c(43);
  for (int i = 0; i < 10; i++) TEST_ASSERT_EQUAL_UINT32(a.next(), b.next());
  TEST_ASSERT_NOT_EQUAL(Rng(42).next(), c.next());
}

void test_rng_zero_seed_is_not_stuck() {
  Rng r(0);
  TEST_ASSERT_NOT_EQUAL(0, r.next());
}

void test_rng_range_is_inclusive_and_bounded() {
  Rng r(1);
  bool sawLo = false, sawHi = false;
  for (int i = 0; i < 2000; i++) {
    uint32_t v = r.range(3, 6);
    TEST_ASSERT_TRUE(v >= 3 && v <= 6);
    sawLo |= v == 3; sawHi |= v == 6;
  }
  TEST_ASSERT_TRUE(sawLo && sawHi);
  TEST_ASSERT_EQUAL_UINT32(7, r.range(7, 7));
}

void test_rng_jitter_bounds() {
  Rng r(5);
  for (int i = 0; i < 1000; i++) {
    uint32_t v = r.jitter(700, 0.2f);
    TEST_ASSERT_TRUE(v >= 560 && v <= 840);
  }
}

void test_trigger_for_event() {
  TEST_ASSERT_EQUAL_INT((int)Trigger::BigHit,  (int)triggerFor(EventType::BigHit));
  TEST_ASSERT_EQUAL_INT((int)Trigger::Cut,     (int)triggerFor(EventType::Cut));
  TEST_ASSERT_EQUAL_INT((int)Trigger::Flurry,  (int)triggerFor(EventType::Flurry));
  TEST_ASSERT_EQUAL_INT((int)Trigger::Swell,   (int)triggerFor(EventType::SwellStart));
  TEST_ASSERT_EQUAL_INT((int)Trigger::Sustain, (int)triggerFor(EventType::SustainStart));
  TEST_ASSERT_EQUAL_INT((int)Trigger::None,    (int)triggerFor(EventType::Pick));
  TEST_ASSERT_EQUAL_INT((int)Trigger::None,    (int)triggerFor(EventType::SustainEnd));
  TEST_ASSERT_EQUAL_INT((int)Trigger::None,    (int)triggerFor(EventType::SwellPeak));
}

void test_priority_order() {
  // Wake > BigHit > Cut > Flurry > Swell > Sustain > DriftOff
  TEST_ASSERT_TRUE(priority(Trigger::Wake)    > priority(Trigger::BigHit));
  TEST_ASSERT_TRUE(priority(Trigger::BigHit)  > priority(Trigger::Cut));
  TEST_ASSERT_TRUE(priority(Trigger::Cut)     > priority(Trigger::Flurry));
  TEST_ASSERT_TRUE(priority(Trigger::Flurry)  > priority(Trigger::Swell));
  TEST_ASSERT_TRUE(priority(Trigger::Swell)   > priority(Trigger::Sustain));
  TEST_ASSERT_TRUE(priority(Trigger::Sustain) > priority(Trigger::DriftOff));
}

void test_bits() {
  TEST_ASSERT_EQUAL_UINT8(1, moodBit(Mood::Asleep));
  TEST_ASSERT_EQUAL_UINT8(8, moodBit(Mood::Hyped));
  TEST_ASSERT_EQUAL_UINT16(1u << 4, eventBit(EventType::SustainEnd));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_rng_is_deterministic_per_seed);
  RUN_TEST(test_rng_zero_seed_is_not_stuck);
  RUN_TEST(test_rng_range_is_inclusive_and_bounded);
  RUN_TEST(test_rng_jitter_bounds);
  RUN_TEST(test_trigger_for_event);
  RUN_TEST(test_priority_order);
  RUN_TEST(test_bits);
  return UNITY_END();
}
