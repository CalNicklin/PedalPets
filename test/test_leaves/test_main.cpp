#include <unity.h>
#include "core/leaves.h"

void setUp() {}
void tearDown() {}

static Rng rng(5);
static LeafField field;

// One leaf resting at x=50 on the feet's depth row.
static void oneLeaf(float x, float depth = 0.75f) {
  field.clear();
  field.add(x, depth, 0);
}
static PetMotion still(float feetX) { return {feetX, 124, 0, 0, 0, feetX}; }

void test_resting_leaf_stays_put() {
  oneLeaf(50);
  for (int i = 0; i < 30; i++) field.step(rng, still(80));
  TEST_ASSERT_TRUE(field.leaf(0).resting);
  TEST_ASSERT_EQUAL_FLOAT(50, field.leaf(0).x);
}

void test_walking_feet_kick_a_nearby_leaf_which_settles_again() {
  oneLeaf(50);
  PetMotion m = still(48);
  m.feetVx = 0.8f;                                  // walking right through it
  field.step(rng, m);
  TEST_ASSERT_FALSE(field.leaf(0).resting);
  float lowest = field.leaf(0).y;
  for (int i = 0; i < 8; i++) { field.step(rng, still(48)); if (field.leaf(0).y < lowest) lowest = field.leaf(0).y; }
  TEST_ASSERT_TRUE(lowest < field.restY(0) - 1);     // it flew up
  TEST_ASSERT_TRUE(field.leaf(0).x > 50);            // in the walking direction
  for (int i = 0; i < 200; i++) field.step(rng, still(48));
  TEST_ASSERT_TRUE(field.leaf(0).resting);
  TEST_ASSERT_EQUAL_FLOAT(field.restY(0), field.leaf(0).y);
}

void test_far_leaves_and_other_depths_are_not_kicked() {
  oneLeaf(90);
  PetMotion m = still(48);
  m.feetVx = 0.8f;
  field.step(rng, m);
  TEST_ASSERT_TRUE(field.leaf(0).resting);
  oneLeaf(50, 0.0f);                                 // back row: feet don't reach it
  field.step(rng, m);
  TEST_ASSERT_TRUE(field.leaf(0).resting);
}

void test_landing_kicks_harder() {
  oneLeaf(50);
  PetMotion m = still(52);
  m.landing = 1.0f;
  field.step(rng, m);
  float minY = field.leaf(0).y;
  for (int i = 0; i < 10; i++) { field.step(rng, still(52)); if (field.leaf(0).y < minY) minY = field.leaf(0).y; }
  TEST_ASSERT_TRUE(minY < field.restY(0) - 4);
}

void test_wing_gust_blows_leaves_away_from_the_pet() {
  oneLeaf(70);
  PetMotion m = still(50);
  m.gust = 1.0f;
  m.gustX = 50;
  for (int i = 0; i < 3; i++) field.step(rng, m);
  for (int i = 0; i < 10; i++) field.step(rng, still(50));
  TEST_ASSERT_TRUE(field.leaf(0).x > 71);
}

void test_leaves_stay_on_screen() {
  oneLeaf(157);
  PetMotion m = still(150);
  m.gust = 1.0f; m.gustX = 120;
  for (int i = 0; i < 100; i++) field.step(rng, m);
  TEST_ASSERT_TRUE(field.leaf(0).x <= 158 && field.leaf(0).x >= 1);
}

void test_motion_sensor() {
  PetMotionSensor s;
  s.update(0, 0, 3, 80, 124);
  PetMotion m = s.update(1.5f, 0, 3, 81.5f, 124);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 1.5f, m.feetVx);
  s.update(1.5f, 10, 3, 81.5f, 124);                 // up in the air
  m = s.update(1.5f, 0, 3, 81.5f, 124);              // back on the ground: a landing
  TEST_ASSERT_TRUE(m.landing > 0.5f);
  m = s.update(1.5f, 0, 160, 81.5f, 124);            // big wing beat
  TEST_ASSERT_TRUE(m.gust > 0.5f);
}

void test_a_moving_hand_sweeps_a_leaf() {
  oneLeaf(50);
  Hand h = {52, 120, -1.5f, 0.2f, false, false};               // sweeping left through it
  field.step(rng, still(100), &h, 1);
  TEST_ASSERT_FALSE(field.leaf(0).resting);
  TEST_ASSERT_TRUE(field.leaf(0).vx < -0.5f);
}

void test_a_closing_fist_picks_up_a_leaf_and_throws_it() {
  oneLeaf(50);
  Hand h = {51, 121, 0, 0, true, true};                 // closing right by it
  field.step(rng, still(100), &h, 1);
  TEST_ASSERT_EQUAL_INT(0, field.leaf(0).heldBy);
  h = {60, 90, 0, -1, true, false};                     // lifted to the face
  field.step(rng, still(100), &h, 1);
  TEST_ASSERT_EQUAL_FLOAT(60, field.leaf(0).x);
  TEST_ASSERT_EQUAL_FLOAT(90, field.leaf(0).y);
  h = {64, 84, 2.5f, -2.0f, false, false};              // hand opens mid-swing
  field.step(rng, still(100), &h, 1);
  TEST_ASSERT_EQUAL_INT(-1, field.leaf(0).heldBy);
  TEST_ASSERT_TRUE(field.leaf(0).vx > 1.5f);
  for (int i = 0; i < 400; i++) field.step(rng, still(100), &h, 0);
  TEST_ASSERT_TRUE(field.leaf(0).resting);              // and it comes down again
}

void test_only_a_closing_hand_grabs() {
  oneLeaf(50);
  Hand h = {51, 121, 0, 0, false, false};
  field.step(rng, still(100), &h, 1);
  TEST_ASSERT_EQUAL_INT(-1, field.leaf(0).heldBy);
  h = {51, 121, 0, 0, true, false};                     // already a fist (dancing): passes by
  field.step(rng, still(100), &h, 1);
  TEST_ASSERT_EQUAL_INT(-1, field.leaf(0).heldBy);
  TEST_ASSERT_TRUE(field.leaf(0).resting);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_resting_leaf_stays_put);
  RUN_TEST(test_walking_feet_kick_a_nearby_leaf_which_settles_again);
  RUN_TEST(test_far_leaves_and_other_depths_are_not_kicked);
  RUN_TEST(test_landing_kicks_harder);
  RUN_TEST(test_wing_gust_blows_leaves_away_from_the_pet);
  RUN_TEST(test_leaves_stay_on_screen);
  RUN_TEST(test_motion_sensor);
  RUN_TEST(test_a_moving_hand_sweeps_a_leaf);
  RUN_TEST(test_a_closing_fist_picks_up_a_leaf_and_throws_it);
  RUN_TEST(test_only_a_closing_hand_grabs);
  return UNITY_END();
}
