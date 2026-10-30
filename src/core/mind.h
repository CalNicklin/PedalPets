#pragma once
#include <math.h>
#include <stdint.h>
#include "directive.h"
#include "intent.h"
#include "mood.h"
#include "music_event.h"
#include "rng.h"

// Mind: the pet's inner life, above the Choreographer. It doesn't animate; it
// decides what the pet is paying attention to and what it wants, so what it
// does is *about* something: it watches the leaf it kicked, gets bored in
// silence, wants you to play again, does a double-take at a sudden hit.
// Outputs: an intent (idle vocabulary), a gaze (where the head points), turn
// requests and a short thought for the telemetry story.

// Head on screen; facing +1 = beak screen-left; reachPx: how far ahead of the
// head its reach move gets to (0 = it can't reach things).
struct Body     { float headX, headY; float facing; float hop; float reachPx; };
struct Sighting { float x, y, vx, vy; bool resting, held; };      // something in the world (a leaf); held = in its hand
struct Gaze     { float look = 0, pitch = 0, eyes = NAN, weight = 0; };

enum class Focus : uint8_t { Nothing, You, Leaf, Spot };
// What it wants its body to do about the focus (the character's approach / reach moves).
enum class Want : uint8_t { None, Approach, Reach };

struct MindConfig {
  uint32_t noticeQuietMs  = 3000;   // a loud hit after this much quiet gets a double-take...
  uint32_t noticeMs       = 200;    // ...lasting this long before the reaction
  uint32_t boredAfterMs   = 5000;   // silence (awake) before boredom starts building
  float    boredRiseMs    = 12000;  // 0 -> 1
  uint32_t wantsYouAfterMs = 2500;  // after you stop playing
  float    wantsYouRiseMs = 4000;
  uint32_t wantsYouMemoryMs = 12000;// only if you played within this long
  float    intentOn       = 0.6f;   // a drive this strong becomes the intent
  uint32_t minIntentMs    = 1500;   // stick with an intent at least this long
  float    lookYou        = 45;     // look (degrees) that turns the head to the viewer
  float    lookAway       = -30;
  float    flyingSpeed    = 0.4f;   // px/frame: a leaf moving faster is "flying"
  float    reachSlack     = 8;      // px either side of its reach that count as in reach
  float    behindMargin   = 6;      // px behind the head before it counts as behind
  uint32_t turnAfterMs    = 500;    // keep watching something behind this long -> turn
  uint32_t landedMemoryMs = 3500;   // a landing stays interesting this long
  float    switchMargin   = 0.15f;  // a new target must beat the current one by this
  float    habituateMs    = 5000;   // watching the same thing gets dull
  uint32_t glanceMinMs    = 900, glanceMaxMs = 2600;
  uint32_t greetMs        = 2500;   // waking to someone it knows: hello for this long
  uint32_t shyMs          = 6000;   // ... to a stranger: a glance, then it keeps its eyes to itself
  float    friendAt       = 0.5f, strangerBelow = 0.15f;
  float    performWeight  = 0.35f;  // gaze weight while dancing (light: the nods and sways show)
};

constexpr int MIND_MAX_SIGHTINGS = 16;

class Mind {
 public:
  explicit Mind(Rng& rng, const MindConfig& cfg = MindConfig()) : rng_(rng), cfg_(cfg) {}

  void reset(uint32_t now);
  // false = held back for a double-take; collect it with takeHeld().
  bool onEvent(const MusicEvent& e, Mood mood, uint32_t now);
  bool takeHeld(uint32_t now, MusicEvent& out);
  void tick(Mood mood, const Body& body, const Sighting* things, int count, uint32_t now);  // once per frame
  bool takeTurn();                         // wants to turn round to face something (once)
  void setFamiliarity(float f) { familiarity_ = f; }   // 0 a stranger .. 1 an old friend (Bond)
  void direct(const Directive& d, uint32_t now);       // a suggestion from the director (optional)
  Want want() const { return want_; }      // this frame

  Intent      intent() const { return intent_; }
  Focus       focus() const { return focus_; }
  const Gaze& gaze() const { return gaze_; }
  const char* thought() const { return thought_; }
  float       boredom() const { return boredom_; }
  float       wantsYou() const { return wantsYou_; }

 private:
  struct Target { Focus focus = Focus::Nothing; int thing = -1; float x = 0, y = 0, salience = 0; bool held = false; };

  void   updateDrives(Mood mood, uint32_t now, float dtMs);
  float  scoreYou(Mood mood, uint32_t now) const;
  Target scoreThing(Mood mood, const Body& body, const Sighting& s, int i, uint32_t now) const;
  Target choose(Mood mood, const Body& body, const Sighting* things, int count, uint32_t now) const;
  void   aim(Mood mood, const Body& body, uint32_t now);
  void   decide(Mood mood, uint32_t now);
  void   act(const Body& body, int count);
  void   think(const char* t) { thought_ = t; }

  Rng&       rng_;
  MindConfig cfg_;
  Intent     intent_ = Intent::None;
  uint32_t   intentSince_ = 0;
  Focus      focus_ = Focus::Nothing;
  Target     target_;
  Gaze       gaze_;
  const char* thought_ = "waking up";
  float      boredom_ = 0, wantsYou_ = 0, youBoost_ = 0;
  uint32_t   lastSound_ = 0, lastPlayed_ = 0, lastTick_ = 0;
  bool       played_ = false;
  bool       holding_ = false, noticing_ = false;
  MusicEvent held_ = {};
  uint32_t   heldUntil_ = 0;
  float      interest_[MIND_MAX_SIGHTINGS];
  bool       wasResting_[MIND_MAX_SIGHTINGS];
  uint32_t   landedAt_[MIND_MAX_SIGHTINGS];
  uint32_t   nextGlance_ = 0, glanceUntil_ = 0;
  float      glanceLook_ = 0, glancePitch_ = 0;
  uint32_t   behindSince_ = 0;
  bool       turn_ = false;
  Want       want_ = Want::None;
  float      familiarity_ = 0;
  Mood       lastMood_ = Mood::Asleep;
  uint32_t   greetUntil_ = 0, shyUntil_ = 0;

  bool greeting(uint32_t now) const { return greetUntil_ && (int32_t)(now - greetUntil_) < 0; }
  bool shy(uint32_t now) const { return shyUntil_ && (int32_t)(now - shyUntil_) < 0; }
  bool directed(uint32_t now) const { return directedUntil_ && (int32_t)(now - directedUntil_) < 0; }
  Directive  directive_;
  uint32_t   directedUntil_ = 0;
};
