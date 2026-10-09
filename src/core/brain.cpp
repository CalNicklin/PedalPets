#include "brain.h"

Brain::Brain(const ArtTables& art, Rng& rng, Performer& performer, const MoodConfig& moodCfg)
    : art_(art), rng_(rng), perf_(performer), mood_(moodCfg) {
  reset(0);
}

void Brain::reset(uint32_t now) {
  mood_.reset(now);
  perf_.reset(mood_.mood(), now);
  for (int i = 0; i < TRIGGER_COUNT; i++) {
    lastVariant_[i] = -1;
    started_[i] = false;
    lastStart_[i] = 0;
    cooldown_[i] = 0;
  }
}

void Brain::onEvent(const MusicEvent& e, uint32_t now) {
  if (mood_.onEvent(e, now) == MoodChange::Woke) {  // event consumed by waking
    fire(Trigger::Wake, now);
    return;
  }
  perf_.onEvent(e.type);
  if (e.type == EventType::Pick) {
    perf_.onPick(e.strength, now);
    return;
  }
  Trigger t = triggerFor(e.type);
  if (t != Trigger::None) fire(t, now);
}

void Brain::tick(const Features& f, uint32_t now) {
  if (mood_.tick(f, now) == MoodChange::FellAsleep) fire(Trigger::DriftOff, now);
  perf_.tick(mood_.mood(), now);
}

void Brain::fire(Trigger t, uint32_t now) {
  int ti = (int)t;
  if (perf_.playing() && perf_.trigger() == t) {  // extend rule
    perf_.extend(now);
    return;
  }
  if (started_[ti] && now - lastStart_[ti] < cooldown_[ti]) return;
  if (!perf_.canInterrupt(t, now)) return;
  int r = pick(t, mood_.mood());
  if (r < 0) return;
  perf_.start(r, t, now);
  lastVariant_[ti] = r;
  started_[ti] = true;
  lastStart_[ti] = now;
  cooldown_[ti] = art_.reactions[r].cooldownMs;
}

bool Brain::matches(int i, Trigger t, Mood m) const {
  const Reaction& r = art_.reactions[i];
  return r.trigger == t && (r.moodMask == 0 || (r.moodMask & moodBit(m)));
}

// Uniform among matching reactions, excluding the last variant used for this
// trigger unless it is the only match.
int Brain::pick(Trigger t, Mood m) {
  int last = lastVariant_[(int)t];
  int fallback = -1, candidates = 0;
  for (int i = 0; i < art_.reactionCount; i++) {
    if (!matches(i, t, m)) continue;
    if (i == last) fallback = i;
    else candidates++;
  }
  if (candidates == 0) return fallback;
  uint32_t k = rng_.range(0, candidates - 1);
  for (int i = 0; i < art_.reactionCount; i++) {
    if (!matches(i, t, m) || i == last) continue;
    if (k-- == 0) return i;
  }
  return fallback;
}
