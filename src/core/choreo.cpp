#include "choreo.h"
#include <math.h>

Choreographer::Choreographer(const Choreography& c, Rng& rng, const ChoreoConfig& cfg)
    : c_(c), rng_(rng), cfg_(cfg) {
  for (int i = 0; i < TRIGGER_COUNT; i++) lastVariant_[i] = -1;
}

void Choreographer::reset(Mood mood, uint32_t now) {
  for (Slot& s : slots_) s = Slot();
  const MoodStyle& st = c_.moods[(int)mood];
  for (int ch = 0; ch < c_.channelCount; ch++) pose_.ch[ch] = stance_[ch] = st.stance[ch] / 4.0f;
  reactionTrigger_ = Trigger::None;
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

// --- starting moves ---------------------------------------------------------------

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

int Choreographer::pickVocab(Mood mood, MoveKind kind) {
  const MoodStyle& st = c_.moods[(int)mood];
  int last = kind == MoveKind::Idle ? lastIdle_ : lastBeatMove_;
  uint32_t total = 0, totalAll = 0;
  for (int i = 0; i < st.vocabCount; i++) {
    const VocabEntry& v = c_.vocab[st.firstVocab + i];
    if (v.kind != kind) continue;
    totalAll += v.weight;
    if (v.move != last) total += v.weight;
  }
  bool avoidLast = total > 0;
  if (!avoidLast) total = totalAll;
  if (total == 0) return -1;
  uint32_t k = rng_.range(0, total - 1);
  for (int i = 0; i < st.vocabCount; i++) {
    const VocabEntry& v = c_.vocab[st.firstVocab + i];
    if (v.kind != kind || (avoidLast && v.move == last)) continue;
    if (k < v.weight) return v.move;
    k -= v.weight;
  }
  return -1;
}

void Choreographer::startIdle(Mood mood, uint32_t now) {
  const MoodStyle& st = c_.moods[(int)mood];
  nextIdle_ = now + rng_.range(st.idleGapMin, st.idleGapMax);
  int move = pickVocab(mood, MoveKind::Idle);
  if (move < 0) return;
  add(move, now, 1.0f, 1.0f);
  lastIdle_ = move;
}

// Beat moves crossfade: a new one starts once the current one is well under way.
void Choreographer::startBeat(Mood mood, uint32_t now) {
  if (reactionSlot()) return;
  for (Slot& s : slots_) {
    if (s.move < 0 || !s.beat || s.target <= 0) continue;
    if (s.frame < cfg_.beatRetrigger * c_.moves[s.move].frames) return;
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

  const MoodStyle& st = c_.moods[(int)mood];
  for (int ch = 0; ch < c_.channelCount; ch++)
    stance_[ch] += (st.stance[ch] / 4.0f - stance_[ch]) * cfg_.stanceEase;

  bool reacting = reactionSlot() != nullptr;
  if (!reacting && (int32_t)(now - nextIdle_) >= 0) startIdle(mood, now);
  if (!reacting && st.beatMs && now - lastPick_ > cfg_.pickTimeoutMs && now - lastBeat_ >= st.beatMs)
    startBeat(mood, now);

  float beatAmp = cfg_.beatAmpBase + cfg_.beatAmpGain * energy;
  for (int ch = 0; ch < c_.channelCount; ch++) {
    float v = stance_[ch];
    for (const Slot& s : slots_)
      if (s.move >= 0) v += s.weight * (s.beat ? beatAmp : 1.0f) * sample(s, ch);
    pose_.ch[ch] = v;
  }

  for (Slot& s : slots_)
    if (s.move >= 0) advance(s, now);
  if (reacting && !reactionSlot()) {               // reaction over: bring the rest back up
    reactionTrigger_ = Trigger::None;
    for (Slot& s : slots_)
      if (s.move >= 0 && s.ducked) { s.target = 1.0f; s.ducked = false; }
  }
}
