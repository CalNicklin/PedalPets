#include <string.h>
#include <unity.h>
#include "core/speech.h"

void setUp() {}
void tearDown() {}

void test_one_line_when_it_fits_else_two_on_words() {
  char lines[2][SPEECH_LINE + 1];
  TEST_ASSERT_EQUAL_INT(1, wrapSpeech("hey... play something?", lines));
  TEST_ASSERT_EQUAL_STRING("hey... play something?", lines[0]);
  TEST_ASSERT_EQUAL_INT(2, wrapSpeech("guess I'm napping until you play again", lines));
  TEST_ASSERT_EQUAL_STRING("guess I'm napping until", lines[0]);
  TEST_ASSERT_EQUAL_STRING("you play again", lines[1]);
  TEST_ASSERT_EQUAL_INT(1, wrapSpeech("whoa!", lines));
  TEST_ASSERT_EQUAL_STRING("whoa!", lines[0]);
}

void test_too_long_ends_in_dots() {
  char lines[2][SPEECH_LINE + 1];
  TEST_ASSERT_EQUAL_INT(2, wrapSpeech("this is a very long thought that goes on and on and on and on", lines));
  TEST_ASSERT_TRUE(strlen(lines[1]) <= SPEECH_LINE);
  TEST_ASSERT_EQUAL_STRING("..", lines[1] + strlen(lines[1]) - 2);
}

void test_a_long_word_is_cut_not_lost() {
  char lines[2][SPEECH_LINE + 1];
  wrapSpeech("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", lines);
  TEST_ASSERT_EQUAL_INT(SPEECH_LINE, (int)strlen(lines[0]));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_one_line_when_it_fits_else_two_on_words);
  RUN_TEST(test_too_long_ends_in_dots);
  RUN_TEST(test_a_long_word_is_cut_not_lost);
  return UNITY_END();
}
