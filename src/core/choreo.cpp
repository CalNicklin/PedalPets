#include "choreo.h"
#include <math.h>

Choreographer::Choreographer(const Choreography& c, Rng& rng, const ChoreoConfig& cfg)
    : c_(c), rng_(rng), cfg_(cfg) {
  for (int i = 0; i < TRIGGER_COUNT; i++) lastVariant_[i] = -1;
}

void Choreographer::reset(Mood mood, uint32_t now) {
  for (Slot& s : slots_) s = Slot();
  for (LiveMark& m : marks_) m = LiveMark();
  const MoodStyle& st = c_.moods[(int)mood];
  for (int ch = 0; ch < c_.channelCount; ch++) pose_.ch[ch] = stance_[ch] = st.stance[ch] / 4.0f;
  stageX_ = 0;
  facing_ = 1;
  if (c_.xChannel >= 0) pose_.ch[c_.xChannel] = stageX_;
  if (c_.faceChannel >= 0) pose_.ch[c_.faceChannel] = facing_;
  reactionTrigger_ = Trigger::None;
  intent_ = Intent::None;
  gazeWeight_ = 0;
  seen_ = 0;
  frozenUntil_ = now;
  lastPick_ = lastBeat_ = now;
  nextIdle_ = now + rng_.range(st.idleGapMin, st.idleGapMax);
  lastIdle_ = lastBeatMove_ = -1;
  for (int i = 0; i < TRIGGER_COUNT; i++) { started_[i] = false; lastVariant_[i] = -1; }
}

// --- queries ---------------------------------------------------------------------

Choreographer::Slot* Choreographer::reactionSlot() {
  for (Slot& s : slots_)
    if (s.move >= 0 && s.reaction) return &s;
  return nullptr;
}

int Choreographer::reaction() const {
  for (const Slot& s : slots_)
    if (s.move >= 0 && s.reaction) return s.move;
  return -1;
}

int Choreographer::activeCount() const {
  int n = 0;
  for (const Slot& s : slots_) n += s.move >= 0;
  return n;
}

int Choreographer::markCount() const {
  int n = 0;
  for (const LiveMark& m : marks_) n += m.mark >= 0;
  return n;
}

MarkFrame Choreographer::markFrame(int i) const {
  for (const LiveMark& m : marks_) {
    if (m.mark < 0) continue;
    if (i-- > 0) continue;
    MarkFrame f = c_.markFrames[c_.marks[m.mark].firstFrame + m.frame];
    if (m.facing < 0) f.dx = (int8_t)(-f.dx - c_.markSizes[f.image].w);   // mirror the offset, not the drawing
    return f;
  }
  return {0, 0, 0};
}

int placeMarks(const Choreography& c, const Choreographer& ch, const DollTables& t,
               const DollPlacement* parts, MarkPlacement* out) {
  if (c.markAnchorPart < 0) return 0;
  const DollPlacement& p = parts[c.markAnchorPart];
  const DollImage& im = t.images[p.image];
  int px = (im.pivotX4 + 2) / 4 - im.x;                // pivot inside the crop
  int ax = p.x + (p.flip ? im.w - px : px);
  int ay = p.y + (im.pivotY4 + 2) / 4 - im.y;
  int n = ch.markCount();
  for (int i = 0; i < n; i++) {
    MarkFrame f = ch.markFrame(i);
    out[i] = {f.image, (int16_t)(ax + f.dx), (int16_t)(ay + f.dy)};
  }
  return n;
}

float Choreographer::weightOf(int move) const {
  float w = 0;
  for (const Slot& s : slots_)
    if (s.move == move) w += s.weight;
  return w;
}

float Choreographer::sample(const Slot& s, int channel) const {
  const Move& m = c_.moves[s.move];
  for (int i = 0; i < m.trackCount; i++) {
    const MoveTrack& tr = c_.tracks[m.firstTrack + i];
    if (tr.channel == channel) return c_.samples[tr.first + s.frame] / 4.0f;
  }
  return 0.0f;
}

float Choreographer::travel(int move) const {
  if (c_.xChannel < 0) return 0;
  const Move& m = c_.moves[move];
  for (int i = 0; i < m.trackCount; i++) {
    const MoveTrack& tr = c_.tracks[m.firstTrack + i];
    if (tr.channel == c_.xChannel) return c_.samples[tr.first + m.frames - 1] / 4.0f;
  }
  return 0;
}

bool Choreographer::allowed(int move) const {
  float x = stageX_ - facing_ * travel(move);   // forward is screen-left when facing +1
  return x >= cfg_.stageMin && x <= cfg_.stageMax;
}

// --- starting moves ---------------------------------------------------------------

void Choreographer::play(int move, uint32_t now) { add(move, now, 1.0f, 1.0f); }

void Choreographer::setIntent(Intent i) { intent_ = i; }

void Choreographer::setGaze(float look, float pitch, float eyes, float weight) {
  gazeLook_ = look;
  gazePitch_ = pitch;
  gazeEyes_ = eyes;
  gazeWeight_ = fmaxf(0.0f, fminf(1.0f, weight));
}

bool Choreographer::requestTurn(uint32_t now) {
  if (c_.turnMove < 0 || reactionSlot()) return false;
  for (const Slot& s : slots_)
    if (s.move >= 0 && turns(s.move) && s.target > 0) return false;   // already turning
  add(c_.turnMove, now, 1.0f, 1.0f);
  lastIdle_ = c_.turnMove;
  return true;
}

Choreographer::Slot* Choreographer::add(int move, uint32_t now, float weight, float target) {
  Slot* slot = nullptr;
  for (Slot& s : slots_)
    if (s.move < 0) { slot = &s; break; }
  if (!slot) {  // full: replace the faintest non-reaction move
    for (Slot& s : slots_)
      if (!s.reaction && (!slot || s.weight < slot->weight)) slot = &s;
  }
  *slot = Slot();
  slot->move = (int8_t)move;
  slot->weight = weight;
  slot->target = target;
  slot->start = now;
  return slot;
}

// Weighted random choice of moves of this kind from a vocabulary: never one
// that would leave the stage, preferably not the last one, and turns favoured
// when heading toward a nearby edge.
int Choreographer::pickVocab(Mood mood, MoveKind kind) {
  const MoodStyle& st = c_.moods[(int)mood];
  return pickFrom(st.firstVocab, st.vocabCount, kind, kind == MoveKind::Idle ? lastIdle_ : lastBeatMove_);
}

int Choreographer::pickFrom(uint16_t first, uint8_t count, MoveKind kind, int last) {
  float heading = -facing_;                       // screen direction of "forward"
  bool nearEdge = (heading < 0 && stageX_ < cfg_.stageMin + cfg_.edgeMargin) ||
                  (heading > 0 && stageX_ > cfg_.stageMax - cfg_.edgeMargin);
  auto weight = [&](const VocabEntry& v) -> uint32_t {
    if (v.kind != kind || !allowed(v.move)) return 0;
    return v.weight * (nearEdge && turns(v.move) ? cfg_.edgeTurnBoost : 1);
  };
  uint32_t total = 0, totalAll = 0;
  for (int i = 0; i < count; i++) {
    const VocabEntry& v = c_.vocab[first + i];
    totalAll += weight(v);
    if (v.move != last) total += weight(v);
  }
  bool avoidLast = total > 0;
  if (!avoidLast) total = totalAll;
  if (total == 0) return -1;
  uint32_t k = rng_.range(0, total - 1);
  for (int i = 0; i < count; i++) {
    const VocabEntry& v = c_.vocab[first + i];
    uint32_t w = weight(v);
    if (!w || (avoidLast && v.move == last)) continue;
    if (k < w) return v.move;
    k -= w;
  }
  return -1;
}

// The intent's idle vocabulary, if it has one (never while asleep).
const IntentStyle* Choreographer::intentStyle(Mood mood) const {
  if (mood == Mood::Asleep || intent_ == Intent::None) return nullptr;
  const IntentStyle& is = c_.intents[(int)intent_];
  return is.vocabCount ? &is : nullptr;
}

void Choreographer::startIdle(Mood mood, uint32_t now) {
  const MoodStyle& st = c_.moods[(int)mood];
  const IntentStyle* is = intentStyle(mood);
  nextIdle_ = now + (is ? rng_.range(is->idleGapMin, is->idleGapMax) : rng_.range(st.idleGapMin, st.idleGapMax));
  int move = is ? pickFrom(is->firstVocab, is->vocabCount, MoveKind::Idle, lastIdle_) : pickVocab(mood, MoveKind::Idle);
  if (move < 0) return;
  add(move, now, 1.0f, 1.0f);
  lastIdle_ = move;
}

// Beat moves crossfade: a new one starts once the current one is well under way
// (long moves, like the flap frenzy, play out nearly to the end).
void Choreographer::startBeat(Mood mood, uint32_t now) {
  if (reactionSlot()) return;
  for (Slot& s : slots_) {
    if (s.move < 0 || !s.beat || s.target <= 0) continue;
    int frames = c_.moves[s.move].frames;
    if (s.frame < fmaxf(cfg_.beatRetrigger * frames, frames - cfg_.beatTailFrames)) return;
    s.target = 0;
  }
  int move = pickVocab(mood, MoveKind::Beat);
  if (move < 0) return;
  Slot* s = add(move, now, 1.0f, 1.0f);
  s->beat = true;
  lastBeat_ = now;
  lastBeatMove_ = move;
}

void Choreographer::fire(Trigger t, Mood mood, uint32_t now) {
  (void)mood;
  int ti = (int)t;
  Slot* r = reactionSlot();
  if (r && reactionTrigger_ == t) {               // same trigger again: extend its loop
    if (c_.moves[r->move].loopLen) r->extend = true;
    return;
  }
  if (started_[ti] && now - lastStart_[ti] < cfg_.cooldownMs) return;
  if (r) {
    if (reactionTrigger_ == Trigger::Wake) return;
    if (reactionTrigger_ != Trigger::DriftOff) {
      if (priority(t) <= priority(reactionTrigger_)) return;
      if (now - r->start < cfg_.interruptGuardMs) return;
    }
    r->target = 0;                                 // old reaction fades out under the new one
    r->reaction = false;
  }
  const ReactionMoves* rm = nullptr;
  for (int i = 0; i < c_.reactionCount; i++)
    if (c_.reactions[i].trigger == t) rm = &c_.reactions[i];
  if (!rm || rm->count == 0) return;
  int pick = 0;
  if (rm->count > 1) {
    pick = (int)rng_.range(0, rm->count - 2);
    if (pick >= lastVariant_[ti] && lastVariant_[ti] >= 0) pick++;
  }
  int move = c_.reactionMoveIds[rm->first + pick];

  for (Slot& s : slots_) {                         // duck everything else
    if (s.move < 0 || s.reaction || s.target <= cfg_.duck) continue;
    s.target = cfg_.duck;
    s.ducked = true;
  }
  Slot* s = add(move, now, cfg_.reactionStart, 1.0f);
  s->reaction = true;
  reactionTrigger_ = t;
  seen_ = 0;
  started_[ti] = true;
  lastStart_[ti] = now;
  lastVariant_[ti] = pick;
  if (c_.moves[move].freezeMs) frozenUntil_ = now + c_.moves[move].freezeMs;
}

// --- events -----------------------------------------------------------------------

void Choreographer::onEvent(const MusicEvent& e, Mood mood, uint32_t now) {
  seen_ |= eventBit(e.type);
  if (e.type == EventType::Pick) {
    lastPick_ = now;
    if (mood == Mood::IntoIt || mood == Mood::Hyped) startBeat(mood, now);
    return;
  }
  Trigger t = triggerFor(e.type);
  if (t != Trigger::None) fire(t, mood, now);
}

void Choreographer::onMoodChange(MoodChange change, Mood mood, uint32_t now) {
  if (change == MoodChange::Woke) fire(Trigger::Wake, mood, now);
  else if (change == MoodChange::FellAsleep) fire(Trigger::DriftOff, mood, now);
}

// --- per frame --------------------------------------------------------------------

void Choreographer::advance(Slot& s, uint32_t now) {
  if (s.weight < s.target) s.weight = fminf(s.target, s.weight + cfg_.fadeStep);
  else if (s.weight > s.target) s.weight = fmaxf(s.target, s.weight - cfg_.fadeStep);
  if (s.target <= 0 && s.weight <= 0) { s.move = -1; return; }
  const Move& m = c_.moves[s.move];
  if (m.flipAt && s.frame + 1 == m.flipAt) facing_ = -facing_;
  s.frame++;
  if (m.loopLen && s.frame == m.loopFrom + m.loopLen) {
    bool again = s.extend;
    if (!again && s.reaction && m.loopUntil != EventType::None && !(seen_ & eventBit(m.loopUntil)))
      again = now - s.start < m.loopMaxMs;
    if (again) { s.extend = false; s.frame = m.loopFrom; }
  }
  if (s.frame >= m.frames) s.move = -1;
}

void Choreographer::tick(Mood mood, float energy, uint32_t now) {
  energy_ = energy;
  if ((int32_t)(now - frozenUntil_) < 0) return;

  for (LiveMark& m : marks_) {                    // marks play out on their own
    if (m.mark < 0) continue;
    if (++m.frame >= c_.marks[m.mark].frameCount) m = LiveMark();
  }

  const MoodStyle& st = c_.moods[(int)mood];
  for (int ch = 0; ch < c_.channelCount; ch++)
    stance_[ch] += (st.stance[ch] / 4.0f - stance_[ch]) * cfg_.stanceEase;

  bool reacting = reactionSlot() != nullptr;
  if (!reacting && (int32_t)(now - nextIdle_) >= 0) startIdle(mood, now);
  if (!reacting && st.beatMs && now - lastPick_ > cfg_.pickTimeoutMs && now - lastBeat_ >= st.beatMs)
    startBeat(mood, now);

  // Travel: x tracks move the pet forward, unweighted (it really goes there).
  if (c_.xChannel >= 0) {
    for (const Slot& s : slots_) {
      if (s.move < 0) continue;
      float d = sample(s, c_.xChannel);
      if (s.frame > 0) {
        Slot prev = s;
        prev.frame--;
        d -= sample(prev, c_.xChannel);
      }
      stageX_ -= facing_ * d;
    }
    // Reactions aren't vetted against the stage; never let them carry it off.
    stageX_ = fmaxf(cfg_.stageMin - 4, fminf(cfg_.stageMax + 4, stageX_));
  }

  for (const Slot& s : slots_) {                  // a move reaching its mark frame pops one up
    if (s.move < 0) continue;
    const Move& m = c_.moves[s.move];
    if (!m.mark || s.frame != m.markAt || s.weight < 0.5f) continue;
    for (LiveMark& lm : marks_) {
      if (lm.mark >= 0) continue;
      lm.mark = (int8_t)(m.mark - 1);
      lm.frame = 0;
      lm.facing = facing_;
      break;
    }
  }

  float beatAmp = cfg_.beatAmpBase + cfg_.beatAmpGain * energy;
  for (int ch = 0; ch < c_.channelCount; ch++) {
    if (ch == c_.xChannel) { pose_.ch[ch] = stageX_; continue; }
    if (ch == c_.faceChannel) { pose_.ch[ch] = facing_; continue; }
    float v = stance_[ch];
    for (const Slot& s : slots_)
      if (s.move >= 0) v += s.weight * (s.beat ? beatAmp : 1.0f) * sample(s, ch);
    pose_.ch[ch] = v;
  }
  if (gazeWeight_ > 0) {                          // the Mind's gaze over the moves
    float w = gazeWeight_;
    if (c_.lookChannel >= 0) pose_.ch[c_.lookChannel] += (gazeLook_ - pose_.ch[c_.lookChannel]) * w;
    if (c_.pitchChannel >= 0) pose_.ch[c_.pitchChannel] += gazePitch_ * w;
    if (c_.eyesChannel >= 0 && !isnan(gazeEyes_) && w >= 0.5f) pose_.ch[c_.eyesChannel] = gazeEyes_;
  }

  for (Slot& s : slots_)
    if (s.move >= 0) advance(s, now);
  if (reacting && !reactionSlot()) {               // reaction over: bring the rest back up
    reactionTrigger_ = Trigger::None;
    for (Slot& s : slots_)
      if (s.move >= 0 && s.ducked) { s.target = 1.0f; s.ducked = false; }
  }
}
