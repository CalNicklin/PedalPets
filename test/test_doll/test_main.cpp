#include <unity.h>
#include "core/doll.h"

void setUp() {}
void tearDown() {}

// Two parts: "base" (ground, one axis over channel 0) and "arm" (child of base,
// one axis summing channels 1 and 2). Channel 3 is the hop.
//   base images: pivot (40,100) for both; anchor for arm at (50,60) / (52,64)
//   arm images:  pivot (10,10) / (12,10)
static const int16_t AXIS_VALUES[] = {0, 1,          // base: shape 0/1
                                      -10, 0, 10};   // arm: angle -10/0/10
static const DollAnchor ANCHORS[] = {{50 * 4, 60 * 4}, {52 * 4, 64 * 4}};
static const DollImage IMAGES[] = {
  // x, y, w, h, pivotX4, pivotY4, firstAnchor
  {30, 50, 20, 50, 40 * 4, 100 * 4, 0},   // base 0
  {30, 52, 22, 48, 40 * 4, 100 * 4, 1},   // base 1
  {5, 5, 10, 10, 10 * 4, 10 * 4, 0},      // arm -10
  {6, 5, 10, 10, 10 * 4, 10 * 4, 0},      // arm 0
  {7, 5, 10, 10, 12 * 4, 10 * 4, 0},      // arm 10
};
static const DollPart PARTS[] = {
  // parent, anchorSlot, axisCount, axes{count, firstValue, sourceMask}x3, firstImage, imageCount
  {-1, 0, 1, {{2, 0, 0b0001}, {0, 0, 0}, {0, 0, 0}}, 0, 2},
  {0, 0, 1, {{3, 2, 0b0110}, {0, 0, 0}, {0, 0, 0}}, 2, 3},
};
static const uint8_t DRAW_ORDER[] = {0, 1};
static const DollTables TABLES = {PARTS, 2, DRAW_ORDER, IMAGES, ANCHORS, AXIS_VALUES, 4, 3};

static DollPose pose(float c0, float c1, float c2, float hop) {
  DollPose p = {};
  p.ch[0] = c0; p.ch[1] = c1; p.ch[2] = c2; p.ch[3] = hop;
  return p;
}

void test_picks_nearest_image_from_summed_channels() {
  DollPlacement out[2];
  composeDoll(TABLES, pose(0, 4, 4, 0), out);    // arm angle 8 -> nearest 10
  TEST_ASSERT_EQUAL_UINT16(0, out[0].image);
  TEST_ASSERT_EQUAL_UINT16(4, out[1].image);
  composeDoll(TABLES, pose(0.6f, -3, -3, 0), out);  // base 0.6 -> 1; arm -6 -> -10
  TEST_ASSERT_EQUAL_UINT16(1, out[0].image);
  TEST_ASSERT_EQUAL_UINT16(2, out[1].image);
}

void test_ties_pick_lower_value() {
  DollPlacement out[2];
  composeDoll(TABLES, pose(0.5f, 5, 0, 0), out);   // exactly between: lower wins
  TEST_ASSERT_EQUAL_UINT16(0, out[0].image);
  TEST_ASSERT_EQUAL_UINT16(3, out[1].image);
}

void test_child_hangs_from_parent_anchor() {
  DollPlacement out[2];
  composeDoll(TABLES, pose(0, 0, 0, 0), out);
  // Ground part at rest: drawn at its crop position.
  TEST_ASSERT_EQUAL_INT16(30, out[0].x);
  TEST_ASSERT_EQUAL_INT16(50, out[0].y);
  // Arm pivot (10,10) moves onto base anchor (50,60): shift (40,50).
  TEST_ASSERT_EQUAL_INT16(6 + 40, out[1].x);
  TEST_ASSERT_EQUAL_INT16(5 + 50, out[1].y);
  // Base image 1 has its anchor at (52,64); arm image 10 has pivot (12,10).
  composeDoll(TABLES, pose(1, 5, 5, 0), out);
  TEST_ASSERT_EQUAL_INT16(7 + 40, out[1].x);
  TEST_ASSERT_EQUAL_INT16(5 + 54, out[1].y);
}

void test_hop_lifts_everything() {
  DollPlacement out[2];
  composeDoll(TABLES, pose(0, 0, 0, 7), out);
  TEST_ASSERT_EQUAL_INT16(50 - 7, out[0].y);
  TEST_ASSERT_EQUAL_INT16(55 - 7, out[1].y);
}

void test_subpixel_anchor_rounds_once() {
  // Quarter-pixel maths, rounded once at the end: 0.4 px stays put, 0.9 px moves 1.
  DollPlacement out[2];
  composeDoll(TABLES, pose(0, 0, 0, 0.4f), out);
  TEST_ASSERT_EQUAL_INT16(50, out[0].y);
  composeDoll(TABLES, pose(0, 0, 0, 0.9f), out);
  TEST_ASSERT_EQUAL_INT16(49, out[0].y);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_picks_nearest_image_from_summed_channels);
  RUN_TEST(test_ties_pick_lower_value);
  RUN_TEST(test_child_hangs_from_parent_anchor);
  RUN_TEST(test_hop_lifts_everything);
  RUN_TEST(test_subpixel_anchor_rounds_once);
  return UNITY_END();
}
