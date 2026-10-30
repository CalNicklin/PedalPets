#pragma once
// The board's side of the director (see core/directive.h): a one-line summary
// of how things are ("S,{json}") every few seconds, and at once when something
// happens (a hit, a cut, waking, the music stopping, a mood change); and
// suggestions back ("#D ..." lines). tools/director.py is the other side.
// Nothing here is needed for the pet to work: with no director it just never
// gets suggestions.
#include <stdio.h>
#include <string.h>
#include "core/directive.h"
#include "platform/doll_pet.h"

class DirectorLink {
 public:
  static constexpr uint32_t SUMMARY_MS = 6000;     // the regular check-in
  static constexpr uint32_t MIN_GAP_MS = 1000;     // moments never come faster than this
  static constexpr uint32_t SILENCE_MS = 4000;     // the music has stopped

  void onEvent(const MusicEvent& e, uint32_t now) {
    lastSound_ = now;
    heard_ = true;
    silenceSaid_ = false;
    if (e.type == EventType::Pick) notes_++;
    else if (e.type == EventType::BigHit || e.type == EventType::Cut || e.type == EventType::Flurry) hits_++;
    if (e.type == EventType::BigHit) moment_ = "big hit";
    else if (e.type == EventType::Cut) moment_ = "cut";
  }

  // "M,<character>,<move>,...": the moves that make sense as gestures (its awake
  // idle and dance vocabularies; not reactions or sleep), sent when the director connects.
  int moves(char* b, int n, const Character& c) const {
    const Choreography& ch = c.choreo;
    bool listed[256] = {};
    int k = snprintf(b, n, "M,%s", c.name);
    auto add = [&](uint16_t first, uint8_t count) {
      for (int i = 0; i < count && k < n - 1; i++) {
        int m = ch.vocab[first + i].move;
        if (listed[m]) continue;
        listed[m] = true;
        k += snprintf(b + k, n - k, ",%s", c.moveNames[m]);
      }
    };
    for (int m = 1; m < MOOD_COUNT; m++) add(ch.moods[m].firstVocab, ch.moods[m].vocabCount);   // awake moods
    for (int i = 0; i < INTENT_COUNT; i++) add(ch.intents[i].firstVocab, ch.intents[i].vocabCount);
    return k;
  }

  // Returns true (and fills b) when a summary is due: regularly, or at once on a moment.
  bool summary(char* b, int n, const DollPet& pet, uint32_t now) {
    static const char* const MOODS[] = {"Asleep", "Curious", "IntoIt", "Hyped"};
    Mood mood = pet.mood.mood();
    if (mood != lastMood_) {
      moment_ = lastMood_ == Mood::Asleep ? "woke up" : mood == Mood::Asleep ? "fell asleep" : "mood changed";
      lastMood_ = mood;
    }
    if (heard_ && !silenceSaid_ && now - lastSound_ >= SILENCE_MS) {
      silenceSaid_ = true;
      if (!moment_) moment_ = "music stopped";
    }
    bool due = now - lastSummary_ >= SUMMARY_MS || (moment_ && now - lastSummary_ >= MIN_GAP_MS);
    if (!due) return false;
    float silence = heard_ ? (now - lastSound_) / 1000.0f : -1;
    snprintf(b, n,
             "S,{\"t\":%u,\"moment\":\"%s\",\"character\":\"%s\",\"mood\":\"%s\",\"energy\":%.2f,\"intent\":\"%s\","
             "\"thought\":\"%s\",\"familiarity\":%.2f,\"silence_s\":%.1f,\"notes\":%d,\"hits\":%d,\"played_s\":%u}",
             (unsigned)now, moment_ ? moment_ : "", pet.character().name, MOODS[(int)mood], pet.mood.energy(),
             intentName(pet.mind.intent()), pet.mind.thought(), pet.bond.familiarity(), silence, notes_, hits_,
             (unsigned)pet.bond.memory().playSeconds);
    lastSummary_ = now;
    notes_ = hits_ = 0;
    moment_ = nullptr;
    return true;
  }

  // Acts on a "#D ..." line: the Mind takes the suggestion; a named move is asked for.
  bool apply(const char* line, DollPet& pet, uint32_t now) {
    pet_ = &pet;
    Directive d;
    if (!parseDirective(line, lookup, &d)) return false;
    pet.mind.direct(d, now);
    if (d.move >= 0) pet.choreo.requestMove(d.move, now);
    return true;
  }

 private:
  static int lookup(const char* name) {
    const Character& c = pet_->character();
    for (int i = 0; i < c.choreo.moveCount; i++)
      if (!strcmp(c.moveNames[i], name)) return i;
    return -1;
  }

  static inline DollPet* pet_ = nullptr;
  uint32_t    lastSummary_ = 0, lastSound_ = 0;
  int         notes_ = 0, hits_ = 0;
  bool        heard_ = false, silenceSaid_ = false;
  Mood        lastMood_ = Mood::Asleep;
  const char* moment_ = nullptr;
};
