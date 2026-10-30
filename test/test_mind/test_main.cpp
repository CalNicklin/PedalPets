#include <math.h>
#include <string.h>
#include <unity.h>
#include "core/mind.h"

void setUp() {}
void tearDown() {}

static Rng rng(1);
static Mind* mind = nullptr;
static uint32_t t;
static Body body = {80, 70, 1, 0, 10};   // head at screen (80, 70), facing screen-left, reaches 10 px ahead

static void freshAsleep() {
  delete mind;
  rng = Rng(1);
  mind = new Mind(rng);
  t = 0;
  mind->reset(t);
}
static void run(Mood m, int frames, const Sighting* s = nullptr, int n = 0);
// Awake and past the wake-up hello (and a stranger's shyness), unless a test is about waking.
static void fresh() {
  freshAsleep();
  run(Mood::Curious, 220);
}
static void run(Mood m, int frames, const Sighting* s, int n) {
  for (int i = 0; i < frames; i++) { t += 30; mind->tick(m, body, s, n, t); }
}
static bool send(EventType e, Mood m, float strength = 1.0f) { return mind->onEvent({e, t, strength}, m, t); }
static void playFor(Mood m, int seconds) {
  for (int i = 0; i < seconds * 4; i++) { send(EventType::Pick, m, 0.6f); run(m, 8); }
}

void test_loud_hit_after_quiet_gets_a_double_take() {
  fresh();
  run(Mood::Curious, 120);                                  // 3.6 s of quiet
  TEST_ASSERT_FALSE(send(EventType::BigHit, Mood::Curious));  // held back
  run(Mood::Curious, 1);
  TEST_ASSERT_EQUAL_FLOAT(45, mind->gaze().look);           // snaps round to you, eyes wide
  TEST_ASSERT_EQUAL_FLOAT(-1, mind->gaze().eyes);
  TEST_ASSERT_EQUAL_FLOAT(1, mind->gaze().weight);
  MusicEvent e;
  TEST_ASSERT_FALSE(mind->takeHeld(t, e));
  run(Mood::Curious, 6);                                    // ~0.2 s later the reaction goes
  TEST_ASSERT_TRUE(mind->takeHeld(t, e));
  TEST_ASSERT_EQUAL(EventType::BigHit, e.type);
}

void test_hit_while_playing_goes_straight_through() {
  fresh();
  playFor(Mood::IntoIt, 2);
  TEST_ASSERT_TRUE(send(EventType::BigHit, Mood::IntoIt));
}

void test_silence_gets_boring() {
  fresh();
  run(Mood::Curious, 30 * 33);                              // 30 s, nobody playing
  TEST_ASSERT_EQUAL(Intent::Bored, mind->intent());
  TEST_ASSERT_NOT_NULL(strstr(mind->thought(), "bored"));
  playFor(Mood::Curious, 2);
  TEST_ASSERT_TRUE(mind->intent() != Intent::Bored);
}

void test_stopping_playing_makes_it_want_you() {
  fresh();
  playFor(Mood::IntoIt, 8);
  run(Mood::Curious, 8 * 33);                               // you stopped 8 s ago
  TEST_ASSERT_EQUAL(Intent::WantsYou, mind->intent());
  TEST_ASSERT_EQUAL(Focus::You, mind->focus());
  TEST_ASSERT_EQUAL_FLOAT(45, mind->gaze().look);
}

void test_a_flying_leaf_is_watched_and_tracked() {
  fresh();
  run(Mood::Curious, 10);
  Sighting leaf = {60, 100, -1.5f, 0.5f, false, false};            // in front, below the head
  run(Mood::Curious, 2, &leaf, 1);
  TEST_ASSERT_EQUAL(Focus::Leaf, mind->focus());
  TEST_ASSERT_EQUAL(Intent::Watch, mind->intent());
  TEST_ASSERT_TRUE(mind->gaze().pitch > 20);                // looks down at it
  TEST_ASSERT_EQUAL_FLOAT(0, mind->gaze().look);
}

void test_a_leaf_landing_gets_investigated() {
  fresh();
  Sighting leaf = {60, 100, -1.5f, 0.5f, false, false};
  run(Mood::Curious, 20, &leaf, 1);
  leaf.vx = leaf.vy = 0;
  leaf.resting = true;
  run(Mood::Curious, 2, &leaf, 1);
  TEST_ASSERT_EQUAL(Intent::Investigate, mind->intent());
  TEST_ASSERT_EQUAL(Focus::Spot, mind->focus());
}

void test_something_behind_makes_it_turn_round() {
  fresh();
  Sighting leaf = {120, 90, 1.0f, 0.3f, false, false};             // behind (beak faces left)
  run(Mood::Curious, 3, &leaf, 1);
  TEST_ASSERT_FALSE(mind->takeTurn());
  run(Mood::Curious, 20, &leaf, 1);
  TEST_ASSERT_TRUE(mind->takeTurn());
  TEST_ASSERT_FALSE(mind->takeTurn());                      // once
}

void test_asleep_has_no_intent_or_gaze() {
  fresh();
  Sighting leaf = {60, 100, -1.5f, 0.5f, false, false};
  run(Mood::Asleep, 30, &leaf, 1);
  TEST_ASSERT_EQUAL(Intent::None, mind->intent());
  TEST_ASSERT_EQUAL_FLOAT(0, mind->gaze().weight);
}

void test_playing_hard_it_performs_to_you() {
  fresh();
  playFor(Mood::Hyped, 3);
  TEST_ASSERT_EQUAL(Intent::None, mind->intent());
  TEST_ASSERT_EQUAL(Focus::You, mind->focus());
  TEST_ASSERT_TRUE(mind->gaze().weight < 1);                // the dance still shows
}

void test_it_walks_up_to_a_landed_leaf_then_reaches_for_it() {
  fresh();
  Sighting leaf = {40, 120, -1.5f, 0.5f, false, false};   // 40 px ahead of the head
  run(Mood::Curious, 10, &leaf, 1);
  leaf.vx = leaf.vy = 0;
  leaf.resting = true;
  run(Mood::Curious, 2, &leaf, 1);
  TEST_ASSERT_EQUAL(Intent::Investigate, mind->intent());
  TEST_ASSERT_EQUAL(Want::Approach, mind->want());
  leaf.x = 69;                                            // now within reach (11 px ahead)
  run(Mood::Curious, 1, &leaf, 1);
  TEST_ASSERT_EQUAL(Want::Reach, mind->want());
  run(Mood::Curious, 1, &leaf, 1);
  TEST_ASSERT_EQUAL(Want::None, mind->want());           // reaches once
}

void test_a_leaf_in_hand_holds_its_attention() {
  fresh();
  Sighting leaf = {70, 60, 0, 0, false, true};            // held up by the face
  run(Mood::Curious, 3, &leaf, 1);
  TEST_ASSERT_EQUAL(Focus::Leaf, mind->focus());
  TEST_ASSERT_TRUE(mind->intent() != Intent::Watch);      // not "watching" (that would use its hands)
  TEST_ASSERT_NOT_NULL(strstr(mind->thought(), "leaf"));
}

static void wakeUp(float familiarity) {
  freshAsleep();
  mind->setFamiliarity(familiarity);
  run(Mood::Asleep, 10);
  send(EventType::Pick, Mood::Asleep);
  run(Mood::Curious, 3);
}

void test_an_old_friend_gets_a_warm_hello() {
  wakeUp(0.9f);
  TEST_ASSERT_NOT_NULL(strstr(mind->thought(), "you're back"));
  TEST_ASSERT_EQUAL(Focus::You, mind->focus());
  TEST_ASSERT_EQUAL(Intent::WantsYou, mind->intent());       // waves, bounces
}

void test_a_stranger_gets_a_shy_glance() {
  wakeUp(0.0f);
  TEST_ASSERT_NOT_NULL(strstr(mind->thought(), "who"));
  TEST_ASSERT_EQUAL(Focus::You, mind->focus());               // a look...
  TEST_ASSERT_TRUE(mind->intent() != Intent::WantsYou);
  run(Mood::Curious, 50);                                     // ...then away
  TEST_ASSERT_TRUE(mind->focus() != Focus::You);
}

void test_a_friend_misses_you_sooner() {
  int when[2];
  for (int k = 0; k < 2; k++) {
    fresh();
    mind->setFamiliarity(k ? 1.0f : 0.0f);
    playFor(Mood::IntoIt, 4);
    int f = 0;
    while (mind->intent() != Intent::WantsYou && f < 2000) { run(Mood::Curious, 1); f++; }
    when[k] = f;
  }
  TEST_ASSERT_TRUE(when[1] < when[0]);
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_loud_hit_after_quiet_gets_a_double_take);
  RUN_TEST(test_hit_while_playing_goes_straight_through);
  RUN_TEST(test_silence_gets_boring);
  RUN_TEST(test_stopping_playing_makes_it_want_you);
  RUN_TEST(test_a_flying_leaf_is_watched_and_tracked);
  RUN_TEST(test_a_leaf_landing_gets_investigated);
  RUN_TEST(test_something_behind_makes_it_turn_round);
  RUN_TEST(test_asleep_has_no_intent_or_gaze);
  RUN_TEST(test_playing_hard_it_performs_to_you);
  RUN_TEST(test_it_walks_up_to_a_landed_leaf_then_reaches_for_it);
  RUN_TEST(test_a_leaf_in_hand_holds_its_attention);
  RUN_TEST(test_an_old_friend_gets_a_warm_hello);
  RUN_TEST(test_a_stranger_gets_a_shy_glance);
  RUN_TEST(test_a_friend_misses_you_sooner);
  return UNITY_END();
}
