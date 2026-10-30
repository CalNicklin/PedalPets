#include <unity.h>
#include "core/memory.h"

void setUp() {}
void tearDown() {}

static uint32_t t;
static void play(Bond& b, Mood m, int seconds) {
  for (int s = 0; s < seconds; s++) {
    for (int i = 0; i < 100; i++) {
      t += 10;
      if (i % 25 == 0) b.onEvent({EventType::Pick, t, 0.6f}, t);
      b.tick(m, t);
    }
  }
}

void test_a_stranger_becomes_a_friend_with_time_played_together() {
  Bond b;
  t = 0;
  b.load(PlayerMemory());
  TEST_ASSERT_EQUAL_FLOAT(0, b.familiarity());
  play(b, Mood::IntoIt, 600);                               // ten minutes
  float ten = b.familiarity();
  TEST_ASSERT_TRUE(ten > 0.15f && ten < 0.5f);
  play(b, Mood::IntoIt, 3000);                              // an hour all told
  TEST_ASSERT_TRUE(b.familiarity() > 0.8f);
  TEST_ASSERT_UINT32_WITHIN(1, 3600, b.memory().playSeconds);   // (the very first tick has no time yet)
}

void test_only_playing_counts_and_hype_is_remembered() {
  Bond b;
  t = 0;
  b.load(PlayerMemory());
  for (int i = 0; i < 3000; i++) { t += 10; b.tick(Mood::Curious, t); }   // 30 s of silence
  TEST_ASSERT_EQUAL_UINT32(0, b.memory().playSeconds);
  play(b, Mood::Hyped, 20);
  TEST_ASSERT_EQUAL_UINT32(20, b.memory().playSeconds);
  TEST_ASSERT_EQUAL_UINT32(20, b.memory().hypedSeconds);
}

void test_sessions_and_saving() {
  Bond b;
  t = 0;
  PlayerMemory m;
  m.sessions = 4;
  m.playSeconds = 100;
  b.load(m);
  b.onWake(t);
  TEST_ASSERT_EQUAL_UINT32(5, b.memory().sessions);
  TEST_ASSERT_TRUE(b.wantsSave(t));                         // a new session is worth keeping
  b.saved(t);
  play(b, Mood::IntoIt, 30);
  TEST_ASSERT_FALSE(b.wantsSave(t));                        // not every few seconds (flash wear)
  play(b, Mood::IntoIt, 40);
  TEST_ASSERT_TRUE(b.wantsSave(t));                         // a minute of new play
}

void test_an_unknown_memory_is_ignored() {
  Bond b;
  PlayerMemory junk;
  junk.version = 99;
  junk.playSeconds = 1000000;
  b.load(junk);
  TEST_ASSERT_EQUAL_UINT32(0, b.memory().playSeconds);
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_a_stranger_becomes_a_friend_with_time_played_together);
  RUN_TEST(test_only_playing_counts_and_hype_is_remembered);
  RUN_TEST(test_sessions_and_saving);
  RUN_TEST(test_an_unknown_memory_is_ignored);
  return UNITY_END();
}
