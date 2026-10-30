#include "mind.h"

namespace {
constexpr float RAD2DEG = 57.29578f;

float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
bool  dancing(Mood m) { return m == Mood::IntoIt || m == Mood::Hyped; }
}  // namespace

void Mind::reset(uint32_t now) {
  intent_ = Intent::None;
  intentSince_ = now;
  focus_ = Focus::Nothing;
  target_ = Target();
  gaze_ = Gaze();
  thought_ = "waking up";
  boredom_ = wantsYou_ = youBoost_ = 0;
  lastSound_ = lastPlayed_ = lastTick_ = now;
  played_ = holding_ = noticing_ = turn_ = false;
  for (int i = 0; i < MIND_MAX_SIGHTINGS; i++) { interest_[i] = 1; wasResting_[i] = true; landedAt_[i] = 0; }
  nextGlance_ = now + rng_.range(cfg_.glanceMinMs, cfg_.glanceMaxMs);
  glanceUntil_ = now;
  behindSince_ = 0;
}

// --- hearing ----------------------------------------------------------------------

bool Mind::onEvent(const MusicEvent& e, Mood mood, uint32_t now) {
  bool quiet = now - lastSound_ >= cfg_.noticeQuietMs;
  lastSound_ = now;
  if (e.type == EventType::Pick) {
    lastPlayed_ = now;
    played_ = true;
    wantsYou_ = 0;
    boredom_ = fmaxf(0.0f, boredom_ - 0.25f);
    youBoost_ = fmaxf(youBoost_, 0.3f * e.strength);
    return true;
  }
  youBoost_ = 1;
  if (e.type == EventType::BigHit && quiet && mood != Mood::Asleep && !holding_) {
    held_ = e;                                   // look first, react a beat later
    holding_ = noticing_ = true;
    heldUntil_ = now + cfg_.noticeMs;
    think("whoa! what was that?");
    return false;
  }
  return true;
}

bool Mind::takeHeld(uint32_t now, MusicEvent& out) {
  if (!holding_ || (int32_t)(now - heldUntil_) < 0) return false;
  holding_ = false;
  out = held_;
  return true;
}

bool Mind::takeTurn() {
  bool t = turn_;
  turn_ = false;
  return t;
}

// --- feeling ----------------------------------------------------------------------

void Mind::updateDrives(Mood mood, uint32_t now, float dtMs) {
  uint32_t silence = now - lastSound_;
  youBoost_ *= expf(-dtMs / 1500.0f);
  if (mood == Mood::Curious && silence > cfg_.boredAfterMs) boredom_ += dtMs / cfg_.boredRiseMs;
  else if (mood != Mood::Curious) boredom_ -= dtMs / 2000.0f;
  bool missed = played_ && now - lastPlayed_ > cfg_.wantsYouAfterMs && now - lastPlayed_ < cfg_.wantsYouMemoryMs;
  if (missed && mood != Mood::Asleep) wantsYou_ += dtMs / cfg_.wantsYouRiseMs;
  else if (!missed) wantsYou_ -= dtMs / 3000.0f;
  boredom_ = clampf(boredom_, 0, 1);
  wantsYou_ = clampf(wantsYou_, 0, 1);
}

// --- attention --------------------------------------------------------------------

float Mind::scoreYou(Mood mood) const {
  return 0.25f + 0.5f * wantsYou_ + youBoost_ + (dancing(mood) ? 0.3f : 0.0f);
}

// How interesting a sighting is right now: a flying leaf (motion, nearness),
// or the spot where one just landed (while curious). Salience 0 = not at all.
Mind::Target Mind::scoreThing(Mood mood, const Body& body, const Sighting& s, int i, uint32_t now) const {
  if (s.held) return {Focus::Leaf, i, s.x, s.y, 0.95f, true};  // in its hand: having a look
  float speed = sqrtf(s.vx * s.vx + s.vy * s.vy);
  float dist = sqrtf((s.x - body.headX) * (s.x - body.headX) + (s.y - body.headY) * (s.y - body.headY));
  float near = clampf(1 - dist / 90.0f, 0, 1) * 0.2f;
  if (!s.resting && speed > cfg_.flyingSpeed)
    return {Focus::Leaf, i, s.x, s.y, (0.5f + fminf(speed, 3.0f) * 0.15f + near) * interest_[i]};
  if (s.resting && landedAt_[i] && now - landedAt_[i] < cfg_.landedMemoryMs && mood == Mood::Curious) {
    float fresh = 1 - (now - landedAt_[i]) / (float)cfg_.landedMemoryMs;
    return {Focus::Spot, i, s.x, s.y, (0.4f + 0.4f * fresh + near) * interest_[i]};
  }
  return {Focus::Nothing, i, s.x, s.y, 0};
}

Mind::Target Mind::choose(Mood mood, const Body& body, const Sighting* things, int count, uint32_t now) const {
  Target best = {Focus::You, -1, 0, 0, scoreYou(mood)};
  for (int i = 0; i < count; i++) {
    Target t = scoreThing(mood, body, things[i], i, now);
    if (t.salience > best.salience) best = t;
  }
  return best;
}

// Point the head at the target (snaps to it, like a bird), or let it go.
void Mind::aim(Mood mood, const Body& body, uint32_t now) {
  if (mood == Mood::Asleep) {
    gaze_.weight = fmaxf(0.0f, gaze_.weight - 0.25f);
    return;
  }
  if (noticing_) {                                 // double-take: round to you, eyes wide
    gaze_ = {cfg_.lookYou, -6, -1, 1};
    if (!holding_) noticing_ = false;
    return;
  }
  float weight = dancing(mood) ? cfg_.performWeight : 1.0f;
  switch (focus_) {
    case Focus::You:
      gaze_ = {cfg_.lookYou, -4, NAN, weight};
      break;
    case Focus::Leaf:
    case Focus::Spot: {
      float dx = target_.x - body.headX, dy = target_.y - body.headY;
      float forward = -dx * body.facing;           // beak is screen-left when facing +1
      if (forward < -cfg_.behindMargin) {          // behind: look over, maybe turn round
        gaze_ = {cfg_.lookAway, 0, NAN, weight};
        if (!behindSince_) behindSince_ = now;
        if (now - behindSince_ >= cfg_.turnAfterMs && body.hop < 1 && target_.salience > 0.5f) {
          turn_ = true;
          behindSince_ = 0;
        }
      } else {
        behindSince_ = 0;
        float pitch = atan2f(dy, fmaxf(fabsf(dx), 8.0f)) * RAD2DEG;
        gaze_ = {0, clampf(pitch, -36, 56), NAN, weight};
      }
      break;
    }
    case Focus::Nothing:
      if ((int32_t)(now - glanceUntil_) < 0) {     // a glance about
        gaze_ = {glanceLook_, glancePitch_, NAN, 1};
      } else {
        gaze_.weight = fmaxf(0.0f, gaze_.weight - 0.25f);
        if ((int32_t)(now - nextGlance_) >= 0) {
          static const float LOOKS[] = {0, 15, -30, 30};
          static const float PITCHES[] = {-20, 24, 0, -8};
          glanceLook_ = LOOKS[(int)rng_.range(0, 3)];
          glancePitch_ = PITCHES[(int)rng_.range(0, 3)];
          glanceUntil_ = now + rng_.range(400, 1200);
          nextGlance_ = glanceUntil_ + rng_.range(cfg_.glanceMinMs, cfg_.glanceMaxMs);
        }
      }
      break;
  }
}

// --- wanting ----------------------------------------------------------------------

void Mind::decide(Mood mood, uint32_t now) {
  Intent want = Intent::None;
  bool holding = focus_ == Focus::Leaf && target_.held;
  if (mood == Mood::Curious) {
    if (holding) want = Intent::Investigate;
    else if (focus_ == Focus::Leaf) want = Intent::Watch;
    else if (focus_ == Focus::Spot) want = Intent::Investigate;
    else if (wantsYou_ >= cfg_.intentOn) want = Intent::WantsYou;
    else if (boredom_ >= cfg_.intentOn) want = Intent::Bored;
  }
  if (want == intent_) return;
  // Noticing things is instant; settling into a mood of wanting takes a moment.
  bool urgent = want == Intent::Watch || want == Intent::Investigate || mood != Mood::Curious;
  if (!urgent && now - intentSince_ < cfg_.minIntentMs) return;
  intent_ = want;
  intentSince_ = now;
}

// Investigating a landed leaf: walk up to it, then reach for it (once).
void Mind::act(const Body& body, int count) {
  want_ = Want::None;
  if (intent_ != Intent::Investigate || focus_ != Focus::Spot || body.reachPx <= 0) return;
  if (target_.thing < 0 || target_.thing >= count) return;
  float forward = (body.headX - target_.x) * body.facing;     // + ahead of it
  if (forward < -cfg_.behindMargin) return;                    // behind: it turns round first
  if (forward > body.reachPx + cfg_.reachSlack) {
    want_ = Want::Approach;
    return;
  }
  want_ = Want::Reach;
  landedAt_[target_.thing] = 0;                                // done with this spot
  interest_[target_.thing] = 0.3f;
}

void Mind::tick(Mood mood, const Body& body, const Sighting* things, int count, uint32_t now) {
  float dtMs = (float)(now - lastTick_);
  lastTick_ = now;
  updateDrives(mood, now, dtMs);

  if (mood == Mood::Asleep) {
    focus_ = Focus::Nothing;
    target_ = Target();
    intent_ = Intent::None;
    holding_ = noticing_ = false;
    aim(mood, body, now);
    think("asleep");
    return;
  }

  if (count > MIND_MAX_SIGHTINGS) count = MIND_MAX_SIGHTINGS;
  for (int i = 0; i < count; i++) {                // notice landings
    if (things[i].resting && !wasResting_[i]) landedAt_[i] = now;
    wasResting_[i] = things[i].resting;
  }
  // Attention: the most interesting thing wins, but the current one keeps it
  // against near rivals (and follows it as it moves).
  Target best = choose(mood, body, things, count, now);
  Target current;
  if (target_.focus == Focus::You) current = {Focus::You, -1, 0, 0, scoreYou(mood)};
  else if (target_.thing >= 0 && target_.thing < count)
    current = scoreThing(mood, body, things[target_.thing], target_.thing, now);
  bool same = best.focus == current.focus && best.thing == current.thing;
  if (same || current.focus == Focus::Nothing || best.salience > current.salience + cfg_.switchMargin)
    target_ = best;
  else
    target_ = current;
  // Watching the same leaf gets dull; the others slowly get interesting again.
  for (int i = 0; i < count && i < MIND_MAX_SIGHTINGS; i++) {
    if (i == target_.thing) interest_[i] = fmaxf(0.1f, interest_[i] - dtMs / cfg_.habituateMs);
    else interest_[i] = fminf(1.0f, interest_[i] + dtMs / (cfg_.habituateMs * 2));
  }
  // You only hold attention when there's reason to look (playing, missing you).
  if (target_.focus == Focus::You && !dancing(mood) && youBoost_ < 0.05f && wantsYou_ < 0.3f && !noticing_)
    target_ = Target();
  focus_ = target_.focus;

  aim(mood, body, now);
  decide(mood, now);
  act(body, count);

  if (noticing_) return;                           // keep "whoa!" until it reacts
  switch (intent_) {
    case Intent::Watch:       think("ooh a leaf - watching it"); break;
    case Intent::Investigate:
      think(target_.held ? "got a leaf - having a look" : "where did it land? going to look");
      break;
    case Intent::WantsYou:    think("hey... play something"); break;
    case Intent::Bored:       think("bored - fidgeting"); break;
    case Intent::None:
      if (mood == Mood::Hyped) think("yes! this rocks");
      else if (mood == Mood::IntoIt) think(focus_ == Focus::Leaf ? "grooving - eyeing a leaf" : "grooving with you");
      else think(focus_ == Focus::You ? "listening to you" : "looking around");
      break;
  }
}
