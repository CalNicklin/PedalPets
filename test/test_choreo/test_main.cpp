#include <math.h>
#include <unity.h>
#include "core/choreo.h"

void setUp() {}
void tearDown() {}

// Channels: 0 hop, 1 a, 2 b, 3 stage x, 4 facing. Samples in quarter units.
static const int16_t SAMPLES[] = {
  0, 4, 8, 0,              // 0 idle_a  (ch1)
  0, 8, 16, 8, 0, 0,       // 1 beat_b  (ch2)
  0, 40, 40, 40, 0,        // 2 react   (ch1)
  0, 20, 20, 20, 20, 0,    // 3 react_loop (ch1), loop frames 1..3
  0, 12, 0,                // 4 wake (ch1)
  0, 40, 0,                // 5 point (ch2), after a freeze
  0, 8, 16, 24, 24, 24,    // 6 hop_fwd: travels 6 px forward (stage x)
  0, 0, 0, 0,              // 7 turn: flips facing at frame 2
};
static const MoveTrack TRACKS[] = {{1, 0}, {2, 4}, {1, 10}, {1, 15}, {1, 21}, {2, 24}, {3, 27}, {1, 33}};
static const Move MOVES[] = {
  // frames, tracks, firstTrack, loopFrom, loopLen, loopUntil, loopMaxMs, freezeMs
  {4, 1, 0, 0, 0, EventType::None, 0, 0},
  {6, 1, 1, 0, 0, EventType::None, 0, 0},
  {5, 1, 2, 0, 0, EventType::None, 0, 0},
  {6, 1, 3, 1, 3, EventType::SustainEnd, 1000, 0},
  {3, 1, 4, 0, 0, EventType::None, 0, 0},
  {3, 1, 5, 0, 0, EventType::None, 0, 300},
  {6, 1, 6, 0, 0, EventType::None, 0, 0},
  {4, 1, 7, 0, 0, EventType::None, 0, 0, 3},   // flipAt = frame 2 (+1)
};
// One mark ("!"): two frames, then gone. REACT (BigHit) spawns it at frame 1.
static const MarkFrame MARK_FRAMES[] = {{0, 2, -20}, {1, 2, -22}};
static const MarkAnim MARKS[] = {{0, 2}};
static Move withMark() {
  Move m = MOVES[2];
  m.mark = 1;      // mark id + 1
  m.markAt = 1;
  return m;
}
static Move MOVES_MARKED[8];
enum { IDLE_A, BEAT_B, REACT, REACT_LOOP, WAKE, POINT, HOP_FWD, TURN };
static const VocabEntry VOCAB[] = {{IDLE_A, 1, MoveKind::Idle}, {BEAT_B, 1, MoveKind::Beat},
                                   {HOP_FWD, 1, MoveKind::Idle}, {TURN, 1, MoveKind::Idle}};
static const uint8_t REACTION_IDS[] = {REACT, REACT_LOOP, WAKE, POINT, REACT_LOOP};
static const ReactionMoves REACTIONS[] = {
  {Trigger::BigHit, 0, 1}, {Trigger::Sustain, 1, 1}, {Trigger::Wake, 2, 1}, {Trigger::Cut, 3, 1},
  {Trigger::Flurry, 4, 1},
};
static Choreography make() {
  Choreography c = {};
  c.xChannel = -1; c.faceChannel = -1;
  for (int i = 0; i < 8; i++) MOVES_MARKED[i] = MOVES[i];
  MOVES_MARKED[2] = withMark();
  c.moves = MOVES_MARKED; c.moveCount = 8; c.tracks = TRACKS; c.samples = SAMPLES;
  c.marks = MARKS; c.markFrames = MARK_FRAMES; c.markCount = 1;
  c.vocab = VOCAB; c.reactions = REACTIONS; c.reactionCount = 5; c.reactionMoveIds = REACTION_IDS;
  c.channelCount = 5; c.xChannel = 3; c.faceChannel = 4;
  c.moods[(int)Mood::Hyped].firstVocab = 2;             // wanders: hop forward or turn
  c.moods[(int)Mood::Hyped].vocabCount = 2;
  c.moods[(int)Mood::Hyped].idleGapMin = 300;
  c.moods[(int)Mood::Hyped].idleGapMax = 300;
  c.moods[(int)Mood::Asleep].stance[1] = 40;           // a = 10 while asleep
  c.moods[(int)Mood::Curious].firstVocab = 0;           // idle_a every 300 ms
  c.moods[(int)Mood::Curious].vocabCount = 1;
  c.moods[(int)Mood::Curious].idleGapMin = 300;
  c.moods[(int)Mood::Curious].idleGapMax = 300;
  c.moods[(int)Mood::IntoIt].firstVocab = 1;            // beat_b on picks
  c.moods[(int)Mood::IntoIt].vocabCount = 1;
  c.moods[(int)Mood::IntoIt].idleGapMin = 60000;
  c.moods[(int)Mood::IntoIt].idleGapMax = 60000;
  c.intents[(int)Intent::Bored] = {2, 1, 300, 300};     // bored: hop forward every 300 ms
  c.lookChannel = 1; c.pitchChannel = 2; c.eyesChannel = -1;
  c.turnMove = TURN;
  return c;
}
static Choreography CH = make();
static Rng rng(1);
static Choreographer* ch = nullptr;
static uint32_t t;

static void frames(Mood m, int n, float energy = 0) {
  for (int i = 0; i < n; i++) { t += 30; ch->tick(m, energy, t); }
}
static void send(EventType e, Mood m) { ch->onEvent({e, t, 1.0f}, m, t); }

static void fresh(Mood m) {
  delete ch;
  rng = Rng(1);
  ch = new Choreographer(CH, rng);
  t = 0;
  ch->reset(m, t);
}

void test_stance_eases_toward_mood() {
  fresh(Mood::Curious);
  TEST_ASSERT_EQUAL_FLOAT(0, ch->pose().ch[1]);
  frames(Mood::Asleep, 1);
  float first = ch->pose().ch[1];
  TEST_ASSERT_TRUE(first > 0 && first < 3);               // glides, no jump
  frames(Mood::Asleep, 60);
  TEST_ASSERT_FLOAT_WITHIN(0.1f, 10.0f, ch->pose().ch[1]);
}

void test_idle_moves_play_on_their_gap() {
  fresh(Mood::Curious);
  frames(Mood::Curious, 10);                              // 300 ms -> idle_a starts
  TEST_ASSERT_TRUE(ch->weightOf(IDLE_A) > 0);
  float peak = 0;
  for (int i = 0; i < 5; i++) { frames(Mood::Curious, 1); if (ch->pose().ch[1] > peak) peak = ch->pose().ch[1]; }
  TEST_ASSERT_TRUE(peak > 0.5f);
}

void test_picks_start_beat_moves_only_when_grooving() {
  fresh(Mood::Curious);
  send(EventType::Pick, Mood::Curious);
  TEST_ASSERT_EQUAL_FLOAT(0, ch->weightOf(BEAT_B));
  fresh(Mood::IntoIt);
  send(EventType::Pick, Mood::IntoIt);
  TEST_ASSERT_TRUE(ch->weightOf(BEAT_B) > 0);
}

void test_rapid_picks_wait_for_beat_move_to_progress() {
  fresh(Mood::IntoIt);
  send(EventType::Pick, Mood::IntoIt);
  frames(Mood::IntoIt, 1);
  send(EventType::Pick, Mood::IntoIt);                    // too soon: same move carries on
  TEST_ASSERT_EQUAL_INT(1, ch->activeCount());
  frames(Mood::IntoIt, 3);
  send(EventType::Pick, Mood::IntoIt);                    // 4/6 through: crossfade to a new one
  TEST_ASSERT_EQUAL_INT(2, ch->activeCount());
}

void test_long_beat_move_plays_until_its_tail() {
  ChoreoConfig cfg;
  cfg.beatTailFrames = 1;                                 // beat_b (6 frames) runs to frame 5
  delete ch;
  rng = Rng(1);
  ch = new Choreographer(CH, rng, cfg);
  t = 0;
  ch->reset(Mood::IntoIt, t);
  send(EventType::Pick, Mood::IntoIt);
  frames(Mood::IntoIt, 4);
  send(EventType::Pick, Mood::IntoIt);                    // 4/6 through but not at its tail: carries on
  TEST_ASSERT_EQUAL_INT(1, ch->activeCount());
  frames(Mood::IntoIt, 1);
  send(EventType::Pick, Mood::IntoIt);                    // at its tail: crossfade
  TEST_ASSERT_EQUAL_INT(2, ch->activeCount());
}

void test_intent_vocabulary_replaces_mood_idles() {
  fresh(Mood::Curious);
  ch->setIntent(Intent::Bored);
  frames(Mood::Curious, 10);                              // 300 ms -> an idle starts
  TEST_ASSERT_TRUE(ch->weightOf(HOP_FWD) > 0);
  TEST_ASSERT_EQUAL_FLOAT(0, ch->weightOf(IDLE_A));
  ch->setIntent(Intent::None);
  frames(Mood::Curious, 20);
  TEST_ASSERT_TRUE(ch->weightOf(IDLE_A) > 0);
}

void test_gaze_points_the_head() {
  fresh(Mood::Curious);
  ch->setGaze(8, 4, NAN, 1.0f);                           // look overrides, pitch adds
  frames(Mood::Curious, 1);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 8, ch->pose().ch[1]);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 4, ch->pose().ch[2]);
  ch->setGaze(8, 4, NAN, 0.5f);
  frames(Mood::Curious, 1);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 4, ch->pose().ch[1]);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 2, ch->pose().ch[2]);
}

void test_requested_turn_plays_the_turn_move_once() {
  fresh(Mood::Curious);
  TEST_ASSERT_TRUE(ch->requestTurn(t));
  TEST_ASSERT_FALSE(ch->requestTurn(t));                  // already turning
  frames(Mood::Curious, 4);
  TEST_ASSERT_EQUAL_FLOAT(-1, ch->pose().ch[4]);
}

void test_reaction_ducks_other_moves() {
  fresh(Mood::Curious);
  frames(Mood::Curious, 10);
  TEST_ASSERT_TRUE(ch->weightOf(IDLE_A) > 0.2f);
  send(EventType::BigHit, Mood::Curious);
  TEST_ASSERT_EQUAL_INT(REACT, ch->reaction());
  frames(Mood::Curious, 3);
  TEST_ASSERT_TRUE(ch->weightOf(IDLE_A) <= 0.21f);
}

void test_reaction_fades_in_not_cut() {
  fresh(Mood::Curious);
  send(EventType::BigHit, Mood::Curious);
  frames(Mood::Curious, 1);
  float w = ch->weightOf(REACT);
  TEST_ASSERT_TRUE(w > 0.3f && w < 1.0f);
}

void test_lower_priority_ignored_during_reaction() {
  fresh(Mood::Curious);
  send(EventType::BigHit, Mood::Curious);
  frames(Mood::Curious, 2);
  send(EventType::SustainStart, Mood::Curious);
  TEST_ASSERT_EQUAL_INT(REACT, ch->reaction());
}

void test_loop_section_holds_until_event() {
  fresh(Mood::Curious);
  send(EventType::SustainStart, Mood::Curious);
  frames(Mood::Curious, 20);
  TEST_ASSERT_EQUAL_INT(REACT_LOOP, ch->reaction());      // still looping
  send(EventType::SustainEnd, Mood::Curious);
  frames(Mood::Curious, 6);
  TEST_ASSERT_EQUAL_INT(-1, ch->reaction());
}

void test_loop_section_caps_at_max() {
  fresh(Mood::Curious);
  send(EventType::SustainStart, Mood::Curious);
  frames(Mood::Curious, 45);                              // 1350 ms > 1000 ms cap
  TEST_ASSERT_EQUAL_INT(-1, ch->reaction());
}

void test_freeze_holds_pose_then_plays() {
  fresh(Mood::Curious);
  frames(Mood::Asleep, 5);                                // pose moving toward asleep stance
  float held = ch->pose().ch[1];
  send(EventType::Cut, Mood::Asleep);
  frames(Mood::Asleep, 9);                                // 270 ms < 300 ms freeze
  TEST_ASSERT_EQUAL_FLOAT(held, ch->pose().ch[1]);
  frames(Mood::Asleep, 3);
  TEST_ASSERT_TRUE(ch->pose().ch[1] > held);              // moving again
}

void test_wake_on_mood_change() {
  fresh(Mood::Asleep);
  ch->onMoodChange(MoodChange::Woke, Mood::Curious, t);
  TEST_ASSERT_EQUAL_INT(WAKE, ch->reaction());
}

void test_travel_moves_along_the_stage_and_stays() {
  fresh(Mood::Curious);
  TEST_ASSERT_EQUAL_FLOAT(1, ch->pose().ch[4]);           // facing default (beak to screen-left)
  ch->play(HOP_FWD, t);
  frames(Mood::Curious, 6);
  TEST_ASSERT_EQUAL_FLOAT(-6, ch->pose().ch[3]);          // forward = screen-left
  frames(Mood::Curious, 5);
  TEST_ASSERT_EQUAL_FLOAT(-6, ch->pose().ch[3]);          // stays where it landed
}

void test_turn_flips_facing_then_travel_reverses() {
  fresh(Mood::Curious);
  ch->play(TURN, t);
  frames(Mood::Curious, 4);
  TEST_ASSERT_EQUAL_FLOAT(-1, ch->pose().ch[4]);
  ch->play(HOP_FWD, t);
  frames(Mood::Curious, 7);
  TEST_ASSERT_EQUAL_FLOAT(6, ch->pose().ch[3]);
}

void test_edge_of_stage_forces_a_turn() {
  fresh(Mood::Hyped);
  for (int i = 0; i < 4; i++) { ch->play(HOP_FWD, t); frames(Mood::Curious, 7); }
  TEST_ASSERT_EQUAL_FLOAT(-24, ch->pose().ch[3]);         // another hop would leave the stage
  for (int i = 0; i < 12; i++) {                          // let the Hyped vocabulary pick
    frames(Mood::Hyped, 1);
    if (ch->weightOf(TURN) > 0 || ch->weightOf(HOP_FWD) > 0) break;
  }
  TEST_ASSERT_TRUE(ch->weightOf(TURN) > 0);
  TEST_ASSERT_EQUAL_FLOAT(0, ch->weightOf(HOP_FWD));
}

void test_moves_spawn_marks_that_play_out() {
  fresh(Mood::Curious);
  send(EventType::BigHit, Mood::Curious);
  TEST_ASSERT_EQUAL_INT(0, ch->markCount());
  frames(Mood::Curious, 2);                       // frame 1 shown -> "!" appears
  TEST_ASSERT_EQUAL_INT(1, ch->markCount());
  TEST_ASSERT_EQUAL_INT(0, ch->markFrame(0).image);
  frames(Mood::Curious, 1);
  TEST_ASSERT_EQUAL_INT(-22, ch->markFrame(0).dy);
  frames(Mood::Curious, 1);
  TEST_ASSERT_EQUAL_INT(0, ch->markCount());      // played out
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_stance_eases_toward_mood);
  RUN_TEST(test_idle_moves_play_on_their_gap);
  RUN_TEST(test_picks_start_beat_moves_only_when_grooving);
  RUN_TEST(test_rapid_picks_wait_for_beat_move_to_progress);
  RUN_TEST(test_long_beat_move_plays_until_its_tail);
  RUN_TEST(test_intent_vocabulary_replaces_mood_idles);
  RUN_TEST(test_gaze_points_the_head);
  RUN_TEST(test_requested_turn_plays_the_turn_move_once);
  RUN_TEST(test_reaction_ducks_other_moves);
  RUN_TEST(test_reaction_fades_in_not_cut);
  RUN_TEST(test_lower_priority_ignored_during_reaction);
  RUN_TEST(test_loop_section_holds_until_event);
  RUN_TEST(test_loop_section_caps_at_max);
  RUN_TEST(test_freeze_holds_pose_then_plays);
  RUN_TEST(test_wake_on_mood_change);
  RUN_TEST(test_travel_moves_along_the_stage_and_stays);
  RUN_TEST(test_turn_flips_facing_then_travel_reverses);
  RUN_TEST(test_edge_of_stage_forces_a_turn);
  RUN_TEST(test_moves_spawn_marks_that_play_out);
  return UNITY_END();
}
