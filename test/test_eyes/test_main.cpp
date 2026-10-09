#include <unity.h>
#include "core/eyes.h"

static Rng rng(3);
static EyeController* eyes = nullptr;
static uint32_t t;

void setUp() {
  rng = Rng(3);
  delete eyes;
  eyes = new EyeController(rng);
  t = 0;
  eyes->reset(t);
}
void tearDown() {}

static void step(Mood m, Eye override = Eye::Auto) { t += 10; eyes->tick(m, override, t); }

void test_first_blink_in_window_and_lasts_120ms() {
  while (eyes->eye() != Eye::Blink && t < 8000) step(Mood::Curious);
  // Due at 2000-6000 ms; a glance in progress can delay it by up to 800 ms.
  TEST_ASSERT_TRUE(t >= 2000 && t <= 6810);
  uint32_t start = t;
  while (eyes->eye() == Eye::Blink) step(Mood::Curious);
  TEST_ASSERT_EQUAL_UINT32(120, t - start);
}

void test_glance_happens() {
  bool glanced = false;
  while (t < 10500) {
    step(Mood::Curious);
    glanced |= eyes->eye() == Eye::LookL || eyes->eye() == Eye::LookR;
  }
  TEST_ASSERT_TRUE(glanced);
}

void test_step_override_wins() {
  step(Mood::Curious, Eye::Wide);
  TEST_ASSERT_EQUAL_INT((int)Eye::Wide, (int)eyes->eye());
}

void test_off_while_asleep_and_rescheduled_on_wake() {
  while (t < 20000) {
    step(Mood::Asleep);
    TEST_ASSERT_EQUAL_INT((int)Eye::Open, (int)eyes->eye());
  }
  uint32_t woke = t;
  while (t < woke + 1990) {
    step(Mood::Curious);
    TEST_ASSERT_EQUAL_INT((int)Eye::Open, (int)eyes->eye());
  }
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_first_blink_in_window_and_lasts_120ms);
  RUN_TEST(test_glance_happens);
  RUN_TEST(test_step_override_wins);
  RUN_TEST(test_off_while_asleep_and_rescheduled_on_wake);
  return UNITY_END();
}
