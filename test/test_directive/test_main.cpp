#include <string.h>
#include <unity.h>
#include "core/directive.h"

void setUp() {}
void tearDown() {}

static int lookupMove(const char* name) { return !strcmp(name, "wave") ? 7 : -1; }

void test_parses_a_full_directive() {
  Directive d;
  TEST_ASSERT_TRUE(parseDirective("#D intent=WantsYou;for=8000;move=wave;look=you;thought=play that riff again?", lookupMove, &d));
  TEST_ASSERT_EQUAL(Intent::WantsYou, d.intent);
  TEST_ASSERT_EQUAL_UINT32(8000, d.forMs);
  TEST_ASSERT_EQUAL_INT(7, d.move);
  TEST_ASSERT_TRUE(d.lookAtYou);
  TEST_ASSERT_EQUAL_STRING("play that riff again?", d.thought);
}

void test_unknown_or_missing_fields_are_left_alone() {
  Directive d;
  TEST_ASSERT_TRUE(parseDirective("#D thought=hmm;move=moonwalk;intent=Dance", lookupMove, &d));
  TEST_ASSERT_EQUAL(Intent::None, d.intent);                 // unknown intent: no change
  TEST_ASSERT_EQUAL_INT(-1, d.move);                         // not in its vocabulary
  TEST_ASSERT_FALSE(d.lookAtYou);
  TEST_ASSERT_EQUAL_UINT32(6000, d.forMs);                   // a default
  TEST_ASSERT_EQUAL_STRING("hmm", d.thought);
}

void test_rejects_other_lines_and_trims_long_thoughts() {
  Directive d;
  TEST_ASSERT_FALSE(parseDirective("hello", lookupMove, &d));
  TEST_ASSERT_TRUE(parseDirective("#D thought=this is a very long thought that goes on and on and on and on", lookupMove, &d));
  TEST_ASSERT_EQUAL_INT(DIRECTIVE_THOUGHT - 1, (int)strlen(d.thought));
  TEST_ASSERT_TRUE(parseDirective("#D thought=a,b", lookupMove, &d));
  TEST_ASSERT_NULL(strchr(d.thought, ','));                  // commas would break the telemetry CSV
  TEST_ASSERT_TRUE(parseDirective("#D thought=say \"hi\"", lookupMove, &d));
  TEST_ASSERT_NULL(strchr(d.thought, '"'));                  // ... and quotes the JSON summary
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_parses_a_full_directive);
  RUN_TEST(test_unknown_or_missing_fields_are_left_alone);
  RUN_TEST(test_rejects_other_lines_and_trims_long_thoughts);
  return UNITY_END();
}
