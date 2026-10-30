#pragma once
// The paper-doll pet's whole loop, shared by the board and the simulator so
// they can't drift apart: music -> mood -> mind -> choreographer -> doll,
// plus the leaves on the ground. Header-only (the simulator builds without
// Arduino); scene drawing stays with the caller.
#include "core/choreo.h"
#include "core/doll.h"
#include "core/leaves.h"
#include "core/mind.h"
#include "core/mood.h"
#include "gen/doll_meta.h"
#include "gen/doll_moves.h"

class DollPet {
 public:
  explicit DollPet(Rng& rng) : mind(rng), choreo(doll_gen::CHOREO, rng), rng_(rng) {}

  // leafColours 0 = no scene (no leaves).
  void reset(uint32_t now, int leafColours, int leafCount) {
    mood.reset(now);
    mind.reset(now);
    choreo.reset(mood.mood(), now);
    motion = PetMotionSensor();
    leaves.clear();
    if (leafColours > 0) leaves.scatter(rng_, leafCount, (uint8_t)leafColours);
    composeDoll(doll_gen::DOLL, choreo.pose(), parts);
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
    Body body = head();
    int n = leaves.count();
    for (int i = 0; i < n; i++) {
      const Leaf& l = leaves.leaf(i);
      sightings_[i] = {l.x, l.y, l.vx, l.vy, l.resting};
    }
    mind.tick(mood.mood(), body, sightings_, n, now);
    if (mind.takeTurn()) choreo.requestTurn(now);
    choreo.setIntent(mind.intent());
    const Gaze& g = mind.gaze();
    choreo.setGaze(g.look, g.pitch, g.eyes, g.weight);

    choreo.tick(mood.mood(), mood.energy(), now);
    composeDoll(doll_gen::DOLL, choreo.pose(), parts);
    markCount = placeMarks(doll_gen::CHOREO, choreo, doll_gen::DOLL, parts, marks);

    int fx, fy;                                   // the pet's feet, in screen pixels
    pivotOnCanvas(doll_gen::DOLL, parts[0], &fx, &fy);
    const DollPose& pose = choreo.pose();
    PetMotion m = motion.update(pose.ch[doll_gen::CH_X], pose.ch[doll_gen::CH_HOP], pose.ch[doll_gen::CH_FLAPL],
                                CANVAS_X + fx, CANVAS_Y + fy);
    leaves.step(rng_, m);
  }

  MoodModel       mood;
  Mind            mind;
  Choreographer   choreo;
  LeafField       leaves;
  PetMotionSensor motion;
  DollPlacement   parts[doll_gen::PART_COUNT];
  MarkPlacement   marks[CHOREO_MAX_MARKS];
  int             markCount = 0;

  static constexpr int CANVAS_X = (160 - doll_gen::CANVAS_W) / 2;   // the doll canvas on screen
  static constexpr int CANVAS_Y = 128 - doll_gen::CANVAS_H;

 private:
  Body head() const {
    int hx, hy;
    pivotOnCanvas(doll_gen::DOLL, parts[doll_gen::P_HEAD], &hx, &hy);
    const DollPose& p = choreo.pose();
    return {(float)(CANVAS_X + hx), (float)(CANVAS_Y + hy), p.ch[doll_gen::CH_FACE], p.ch[doll_gen::CH_HOP]};
  }

  Rng&     rng_;
  Sighting sightings_[MAX_LEAVES];
};
