#include <unity.h>
#include "core/crowd.h"

void setUp() {}
void tearDown() {}

static Rng rng(3);
static Crowd* crowd = nullptr;
static uint32_t t;

static void fresh(int n = 4) {
  delete crowd;
  rng = Rng(3);
  crowd = new Crowd(rng);
  t = 0;
  crowd->reset(n, t);
}
static void run(Mood m, float energy, int frames) {
  for (int i = 0; i < frames; i++) { t += 30; crowd->tick(m, energy, t); }
}
static int countPose(CritterPose p) {
  int n = 0;
  for (int i = 0; i < crowd->count(); i++) n += crowd->pose(i) == p;
  return n;
}
static int out() { return crowd->count() - countPose(CritterPose::Hidden); }

void test_asleep_they_stay_hidden_but_peek_now_and_then() {
  fresh();
  run(Mood::Asleep, 0, 30);
  TEST_ASSERT_EQUAL_INT(0, out());
  int peeks = 0;
  for (int i = 0; i < 1500; i++) { run(Mood::Asleep, 0, 1); peeks += countPose(CritterPose::Peek) > 0; }
  TEST_ASSERT_TRUE(peeks > 0);                               // someone looked out in 45 s
  TEST_ASSERT_TRUE(peeks < 1000);                            // but mostly nobody
}

void test_they_come_out_as_the_music_builds_eyes_first() {
  fresh();
  run(Mood::IntoIt, 0.6f, 6);
  TEST_ASSERT_TRUE(countPose(CritterPose::Up) == 0);         // not all at once: eyes first
  run(Mood::IntoIt, 0.6f, 80);
  TEST_ASSERT_TRUE(out() >= 3);
  TEST_ASSERT_EQUAL_INT(0, countPose(CritterPose::Cheer));
}

void test_hyped_they_cheer_and_bob_on_the_beat() {
  fresh();
  run(Mood::Hyped, 0.9f, 80);
  TEST_ASSERT_EQUAL_INT(4, out());
  bool cheered = false, bobbed = false;
  for (int k = 0; k < 8; k++) {
    crowd->onEvent({EventType::Pick, t, 0.9f}, t);
    run(Mood::Hyped, 0.9f, 1);
    for (int i = 0; i < 4; i++) bobbed |= crowd->dip(i) > 0;
    run(Mood::Hyped, 0.9f, 15);
    cheered |= countPose(CritterPose::Cheer) > 0;
  }
  TEST_ASSERT_TRUE(cheered);
  TEST_ASSERT_TRUE(bobbed);
}

void test_a_big_hit_makes_them_duck_then_come_back() {
  fresh();
  run(Mood::IntoIt, 0.6f, 80);
  int before = countPose(CritterPose::Up) + countPose(CritterPose::Cheer);
  TEST_ASSERT_TRUE(before > 0);
  crowd->onEvent({EventType::BigHit, t, 1.0f}, t);
  run(Mood::IntoIt, 0.6f, 2);
  TEST_ASSERT_EQUAL_INT(0, countPose(CritterPose::Up) + countPose(CritterPose::Cheer));   // all ducked
  run(Mood::IntoIt, 0.6f, 40);
  TEST_ASSERT_TRUE(countPose(CritterPose::Up) + countPose(CritterPose::Cheer) > 0);
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_asleep_they_stay_hidden_but_peek_now_and_then);
  RUN_TEST(test_they_come_out_as_the_music_builds_eyes_first);
  RUN_TEST(test_hyped_they_cheer_and_bob_on_the_beat);
  RUN_TEST(test_a_big_hit_makes_them_duck_then_come_back);
  return UNITY_END();
}
