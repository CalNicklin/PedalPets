#pragma once
// The pet's whole loop, shared by the board and the simulator so they can't
// drift apart: music -> mood -> mind -> choreographer -> doll, plus the leaves
// on the ground. It knows nothing about any particular character or scene:
// those come in as packs (core/pack.h) and can be swapped at run time.
#include "core/choreo.h"
#include "core/doll.h"
#include "core/leaves.h"
#include "core/mind.h"
#include "core/mood.h"
#include "core/pack.h"

constexpr int SCREEN_W = 160, SCREEN_H = 128;

class DollPet {
 public:
  DollPet(const Character& c, Rng& rng) : mind(rng), choreo(c.choreo, rng), rng_(rng), char_(&c) {}

  void setCharacter(const Character& c) { char_ = &c; choreo.bind(c.choreo); }   // then reset()
  void setScene(const Scene* s) { scene_ = s; }                                   // then reset()
  const Character& character() const { return *char_; }
  const Scene*     scene() const { return scene_; }

  void reset(uint32_t now, int leafCount) {
    mood.reset(now);
    mind.reset(now);
    choreo.reset(mood.mood(), now);
    motion = PetMotionSensor();
    leaves.clear();
    if (scene_ && scene_->leafColours) leaves.scatter(rng_, leafCount, scene_->leafColours);
    composeDoll(char_->doll, choreo.pose(), parts);
    markCount = 0;
    handsSeen_ = false;
  }

  // A music event (10 ms logic tick). The Mind may hold a sudden hit back for
  // a double-take; it comes out of tick() a moment later.
  void event(const MusicEvent& e, uint32_t now) {
    MoodChange c = mood.onEvent(e, now);
    if (c == MoodChange::Woke) { choreo.onMoodChange(c, mood.mood(), now); return; }  // waking eats the event
    if (mind.onEvent(e, mood.mood(), now)) choreo.onEvent(e, mood.mood(), now);
  }

  void tick(const Features& f, uint32_t now) {
    MusicEvent held;
    if (mind.takeHeld(now, held)) choreo.onEvent(held, mood.mood(), now);
    MoodChange c = mood.tick(f, now);
    if (c != MoodChange::None) choreo.onMoodChange(c, mood.mood(), now);
  }

  // Once per display frame: think, move, compose, then the world reacts.
  void frame(uint32_t now) {
    const Character& ch = *char_;
    Body body = head();
    int n = leaves.count();
    for (int i = 0; i < n; i++) {
      const Leaf& l = leaves.leaf(i);
      sightings_[i] = {l.x, l.y, l.vx, l.vy, l.resting, l.heldBy >= 0};
    }
    mind.tick(mood.mood(), body, sightings_, n, now);
    if (mind.takeTurn()) choreo.requestTurn(now);
    if (mind.want() == Want::Approach) choreo.requestMove(ch.approachMove, now);
    else if (mind.want() == Want::Reach) choreo.requestMove(ch.reachMove, now);
    choreo.setIntent(mind.intent());
    const Gaze& g = mind.gaze();
    choreo.setGaze(g.look, g.pitch, g.eyes, g.weight);

    choreo.tick(mood.mood(), mood.energy(), now);
    composeDoll(ch.doll, choreo.pose(), parts);
    markCount = placeMarks(ch.choreo, choreo, ch.doll, parts, marks);
    for (int i = 0; i < markCount; i++)          // keep marks on screen (a popped skull lifts them)
      if (canvasY() + marks[i].y < 1) marks[i].y = (int16_t)(1 - canvasY());

    int fx, fy;                                   // the pet's feet (the ground part's pivot), on screen
    pivotOnCanvas(ch.doll, parts[0], &fx, &fy);
    PetMotion m = motion.update(channel(ch.doll.xChannel), channel(ch.doll.hopChannel), channel(ch.gustChannel),
                                canvasX() + fx, canvasY() + fy);
    handCount_ = updateHands();
    leaves.step(rng_, m, hands_, handCount_);
  }

  const Hand* hands(int* count) const { *count = handCount_; return hands_; }   // this frame's hands

  int canvasX() const { return (SCREEN_W - char_->canvasW) / 2; }   // the doll canvas, bottom-centred
  int canvasY() const { return SCREEN_H - char_->canvasH; }

  MoodModel       mood;
  Mind            mind;
  Choreographer   choreo;
  LeafField       leaves;
  PetMotionSensor motion;
  DollPlacement   parts[DOLL_MAX_PARTS];
  MarkPlacement   marks[CHOREO_MAX_MARKS];
  int             markCount = 0;

 private:
  float channel(int c) const { return c >= 0 ? choreo.pose().ch[c] : 0.0f; }

  // Where the hands are on screen this frame, how fast they move, whether they grip.
  int updateHands() {
    const Character& ch = *char_;
    int n = 0;
    for (int k = 0; k < 2; k++) {
      int part = ch.handParts[k];
      int x, y;
      if (part < 0 || !tipOnCanvas(ch.doll, part, parts[part], &x, &y)) continue;
      float sx = (float)(canvasX() + x), sy = (float)(canvasY() + y);
      float g = channel(ch.gripChannels[k]);
      bool grip = g >= 0.5f && g < 1.5f;
      hands_[n] = {sx, sy, handsSeen_ ? sx - lastHand_[k][0] : 0, handsSeen_ ? sy - lastHand_[k][1] : 0, grip,
                   grip && handsSeen_ && !lastGrip_[k]};
      lastHand_[k][0] = sx;
      lastHand_[k][1] = sy;
      lastGrip_[k] = grip;
      n++;
    }
    handsSeen_ = true;
    return n;
  }

  Body head() const {
    int hx = 0, hy = 0;
    if (char_->headPart >= 0) pivotOnCanvas(char_->doll, parts[char_->headPart], &hx, &hy);
    float face = char_->doll.faceChannel >= 0 ? channel(char_->doll.faceChannel) : 1.0f;
    return {(float)(canvasX() + hx), (float)(canvasY() + hy), face, channel(char_->doll.hopChannel),
            char_->reachMove >= 0 ? (float)char_->reachPx : 0.0f};
  }

  Rng&             rng_;
  const Character* char_;
  const Scene*     scene_ = nullptr;
  Sighting         sightings_[MAX_LEAVES];
  Hand             hands_[2];
  float            lastHand_[2][2] = {};
  bool             lastGrip_[2] = {};
  bool             handsSeen_ = false;
  int              handCount_ = 0;
};
