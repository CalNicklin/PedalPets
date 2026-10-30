#pragma once
#include <math.h>
#include <stdint.h>
#include "art_tables.h"
#include "doll.h"
#include "intent.h"
#include "mood.h"
#include "music_event.h"
#include "rng.h"

// Choreographer: drives a paper doll by layering authored moves over a mood
// stance. Moves fade in and out and overlap, so the pet never cuts between
// clips: moods glide, beats crossfade, reactions duck everything else.

// A move channel track: samples[first + frame], in quarter units.
struct MoveTrack { uint8_t channel; uint16_t first; };

struct Move {
  uint8_t   frames;
  uint8_t   trackCount;
  uint16_t  firstTrack;
  uint8_t   loopFrom, loopLen;   // loop section; loopLen 0 = none
  EventType loopUntil;           // repeat while waiting for it (None = only when extended)
  uint16_t  loopMaxMs;           // from move start
  uint16_t  freezeMs;            // hold the current pose this long first (Cut)
  uint8_t   flipAt;              // turn round after showing frame flipAt-1 (0 = never)
  uint8_t   mark;                // expression mark to pop up (id + 1; 0 = none) ...
  uint8_t   markAt;              // ... each time this frame is shown
};

// Expression marks ("!", notes, zzz...): little drawings near the head with
// their own short animation. Offsets are from the anchor part's pivot to the
// mark's top-left, for the default facing; marks are never mirrored.
struct MarkFrame { uint8_t image; int8_t dx, dy; };
struct MarkAnim  { uint16_t firstFrame; uint8_t frameCount; };
struct MarkSize  { uint8_t w, h; };
struct MarkPlacement { uint8_t image; int16_t x, y; };

enum class MoveKind : uint8_t { Idle, Beat };
struct VocabEntry { uint8_t move; uint8_t weight; MoveKind kind; };

struct MoodStyle {
  int16_t  stance[DOLL_MAX_CHANNELS];   // quarter units
  uint16_t firstVocab;
  uint8_t  vocabCount;
  uint16_t idleGapMin, idleGapMax;      // ms between idle moves
  uint16_t beatMs;                      // beat-move tempo with no picks (0 = none)
};

struct ReactionMoves { Trigger trigger; uint8_t first; uint8_t count; };  // into reactionMoveIds

// An intent's idle vocabulary (into vocab); vocabCount 0 = keep the mood's.
struct IntentStyle { uint16_t firstVocab; uint8_t vocabCount; uint16_t idleGapMin, idleGapMax; };

struct Choreography {
  const Move*          moves;
  uint8_t              moveCount;
  const MoveTrack*     tracks;
  const int16_t*       samples;
  MoodStyle            moods[MOOD_COUNT];
  const VocabEntry*    vocab;
  const ReactionMoves* reactions;
  uint8_t              reactionCount;
  const uint8_t*       reactionMoveIds;
  uint8_t              channelCount;
  // Stage position and facing persist (they are where the pet *is*, not a
  // pose): x tracks are travel in the facing direction, accumulated frame by
  // frame; facing flips at a move's flipAt. -1 = the doll has no such channel.
  int8_t               xChannel;
  int8_t               faceChannel;
  const MarkAnim*      marks;
  const MarkFrame*     markFrames;
  uint8_t              markCount;
  const MarkSize*      markSizes;       // per mark image
  int8_t               markAnchorPart;  // doll part the marks hover by (the head)
  IntentStyle          intents[INTENT_COUNT];
  // Head channels the Mind's gaze steers, and the move it turns round with (-1 = none).
  int8_t               lookChannel, pitchChannel, eyesChannel;
  int8_t               turnMove;
};

struct ChoreoConfig {
  float    stanceEase       = 0.15f;   // per frame, toward the mood stance
  float    fadeStep         = 0.25f;   // weight change per frame
  float    duck             = 0.2f;    // other moves' weight during a reaction
  float    reactionStart    = 0.4f;    // reactions start at this weight (instant but not a cut)
  uint32_t interruptGuardMs = 120;
  uint32_t cooldownMs       = 1500;
  float    beatRetrigger    = 0.6f;    // a new beat move waits until the last is this far through
  int      beatTailFrames   = 12;      // ...or, for long moves, until it is this close to its end
  uint32_t pickTimeoutMs    = 1500;    // no picks for this long -> mood tempo drives beats
  float    beatAmpBase      = 0.7f;    // beat moves scale with energy: base + energy * gain
  float    beatAmpGain      = 0.5f;
  float    stageMin         = -28;     // stage x range (pixels)
  float    stageMax         = 28;
  float    edgeMargin       = 12;      // heading toward an edge this close -> prefer turning
  uint32_t edgeTurnBoost    = 4;       // weight multiplier for turns near an edge
};

constexpr int CHOREO_MAX_ACTIVE = 8;
constexpr int CHOREO_MAX_MARKS  = 3;

class Choreographer {
 public:
  Choreographer(const Choreography& c, Rng& rng, const ChoreoConfig& cfg = ChoreoConfig());

  void reset(Mood mood, uint32_t now);
  void onEvent(const MusicEvent& e, Mood mood, uint32_t now);
  void onMoodChange(MoodChange change, Mood mood, uint32_t now);
  void tick(Mood mood, float energy, uint32_t now);   // once per display frame
  void play(int move, uint32_t now);                  // start a move directly (tests, debug)

  // From the Mind: what it wants (idle vocabulary), where it's looking, and
  // turning round to face something. Gaze: look replaces the moves' look,
  // pitch adds to theirs, eyes (NAN = leave) override; all by weight 0..1.
  void setIntent(Intent i);
  void setGaze(float look, float pitch, float eyes, float weight);
  bool requestTurn(uint32_t now);                     // false if it can't turn now

  const DollPose& pose() const { return pose_; }
  int  reaction() const;                     // move id of the active reaction, or -1
  int  activeCount() const;
  int  markCount() const;
  MarkFrame markFrame(int i) const;          // current frame of the i-th live mark, dx facing-adjusted
  float weightOf(int move) const;            // summed weight of a move's active slots

 private:
  struct Slot {
    int8_t   move = -1;
    uint8_t  frame = 0;
    float    weight = 0, target = 0;
    bool     reaction = false, beat = false, extend = false, ducked = false;
    uint32_t start = 0;
  };

  void fire(Trigger t, Mood mood, uint32_t now);
  void startIdle(Mood mood, uint32_t now);
  void startBeat(Mood mood, uint32_t now);
  int  pickVocab(Mood mood, MoveKind kind);
  int  pickFrom(uint16_t first, uint8_t count, MoveKind kind, int last);
  const IntentStyle* intentStyle(Mood mood) const;
  Slot* add(int move, uint32_t now, float weight, float target);
  Slot* reactionSlot();
  void advance(Slot& s, uint32_t now);
  float sample(const Slot& s, int channel) const;
  float travel(int move) const;              // forward distance a move covers (pixels)
  bool  allowed(int move) const;             // stays on stage?
  bool  turns(int move) const { return c_.moves[move].flipAt != 0; }

  const Choreography& c_;
  Rng&                rng_;
  ChoreoConfig        cfg_;
  Slot                slots_[CHOREO_MAX_ACTIVE];
  float               stance_[DOLL_MAX_CHANNELS] = {};
  DollPose            pose_ = {};
  Trigger             reactionTrigger_ = Trigger::None;
  uint16_t            seen_ = 0;
  uint32_t            frozenUntil_ = 0;
  uint32_t            nextIdle_ = 0, lastPick_ = 0, lastBeat_ = 0;
  int                 lastIdle_ = -1, lastBeatMove_ = -1;
  int                 lastVariant_[TRIGGER_COUNT];
  bool                started_[TRIGGER_COUNT] = {};
  uint32_t            lastStart_[TRIGGER_COUNT] = {};
  float               energy_ = 0;
  struct LiveMark { int8_t mark = -1; uint8_t frame = 0; float facing = 1; };
  LiveMark            marks_[CHOREO_MAX_MARKS];
  float               stageX_ = 0;           // pixels; + is screen-right
  float               facing_ = 1;           // +1 beak to screen-left (as rendered), -1 mirrored
  Intent              intent_ = Intent::None;
  float               gazeLook_ = 0, gazePitch_ = 0, gazeEyes_ = NAN, gazeWeight_ = 0;
};

// Screen positions for the live marks, hovering by the anchor part.
int placeMarks(const Choreography& c, const Choreographer& ch, const DollTables& t,
               const DollPlacement* parts, MarkPlacement* out);
