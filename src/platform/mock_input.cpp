#include "mock_input.h"
#include <math.h>

void MockInput::reset() {
  count_ = 0;
  base_ = lift_ = 0;
  script_ = nullptr;
}

void MockInput::key(char c, uint32_t now) {
  switch (c) {
    case 'p': schedule(EventType::Pick, 0.4f, now); break;
    case 'P': schedule(EventType::Pick, 0.9f, now); break;
    case 'h': schedule(EventType::BigHit, 1.0f, now); lift(1.0f, now); break;
    case 'f':
      for (int i = 0; i < 8; i++) schedule(EventType::Pick, 0.7f, now + i * 80);
      schedule(EventType::Flurry, 1.0f, now + 160);
      break;
    case 's': schedule(EventType::SustainStart, 1.0f, now); base_ = fmaxf(base_, 0.5f); break;
    case 'S': schedule(EventType::SustainEnd, 1.0f, now); base_ = 0.1f; break;
    case 'w': schedule(EventType::SwellStart, 1.0f, now); break;
    case 'W': schedule(EventType::SwellPeak, 1.0f, now); lift(1.0f, now); break;
    case 'c': schedule(EventType::Cut, 1.0f, now); base_ = 0; lift_ = 0; break;
    case '+': base_ = fminf(1.0f, base_ + 0.1f); break;
    case '-': base_ = fmaxf(0.0f, base_ - 0.1f); break;
    case '0': base_ = 0; lift_ = 0; break;
    case '1': case '2': case '3': case '4': runScript(c - '1', now); break;
    case 'd': hud_ = true; break;
    case 't': telemetry_ = true; break;
    case 'r': reset_ = true; break;
    case 'n': nextChar_ = true; break;    // next character pack
    case 'b': nextScene_ = true; break;   // next scene (backdrop)
    case 'x': forget_ = true; break;      // forget the player (memory wiped)
    case 'g': director_ = true; break;    // director mode on/off (summaries out, suggestions in)
    default: break;  // includes \r and \n from the serial monitor
  }
}

void MockInput::schedule(EventType type, float strength, uint32_t at) {
  if (count_ < QUEUE) queue_[count_++] = {type, at, strength};
}

void MockInput::runScript(int n, uint32_t now) {
  if (n < 0 || n >= SCRIPT_COUNT || SCRIPTS[n].count > MAX_SCRIPT) return;
  script_ = &SCRIPTS[n];
  scriptStart_ = now;
  for (int i = 0; i < MAX_SCRIPT; i++) fired_[i] = 0;
}

void MockInput::tick(uint32_t now) {
  if (!script_) return;
  // Keys arrive on millis() but ticks run on the (slightly earlier) grid; an
  // unsigned now - scriptStart_ would wrap and fire the whole script at once.
  if ((int32_t)(now - scriptStart_) < 0) return;
  bool done = true;
  for (int i = 0; i < script_->count; i++) {
    const ScriptEntry& e = script_->entries[i];
    while (fired_[i] < e.repeat && now - scriptStart_ >= e.t_ms + fired_[i] * (uint32_t)e.every_ms) {
      fired_[i]++;
      key(e.key, now);
    }
    if (fired_[i] < e.repeat) done = false;
  }
  if (done) script_ = nullptr;
}

bool MockInput::pop(uint32_t now, MusicEvent& out) {
  int best = -1;
  for (int i = 0; i < count_; i++) {
    if ((int32_t)(now - queue_[i].t_ms) < 0) continue;
    if (best < 0 || (int32_t)(queue_[i].t_ms - queue_[best].t_ms) < 0) best = i;
  }
  if (best < 0) return false;
  out = queue_[best];
  for (int i = best; i < count_ - 1; i++) queue_[i] = queue_[i + 1];  // keep arrival order
  count_--;
  if (out.type == EventType::Pick) lift(out.strength, now);
  return true;
}

void MockInput::lift(float level, uint32_t now) {
  lift_ = fmaxf(liftNow(now), level);
  liftAt_ = now;
}

float MockInput::liftNow(uint32_t now) const {
  float k = 1.0f - (float)(now - liftAt_) / LIFT_MS;
  return k > 0 ? lift_ * k : 0.0f;
}

Features MockInput::features(uint32_t now) const {
  return {fmaxf(base_, liftNow(now)), 0.0f};
}
