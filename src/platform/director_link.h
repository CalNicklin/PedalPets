#pragma once
// The board's side of the director (see core/directive.h): every few seconds
// a one-line summary of how things are ("S,{json}"), and suggestions back
// ("#D ..." lines). tools/director.py is the other side. Nothing here is
// needed for the pet to work: with no director it just never gets suggestions.
#include <stdio.h>
#include <string.h>
#include "core/directive.h"
#include "platform/doll_pet.h"

class DirectorLink {
 public:
  static constexpr uint32_t SUMMARY_MS = 6000;

  void onEvent(const MusicEvent& e, uint32_t now) {
    lastSound_ = now;
    heard_ = true;
    if (e.type == EventType::Pick) notes_++;
    else if (e.type == EventType::BigHit || e.type == EventType::Cut || e.type == EventType::Flurry) hits_++;
  }

  // "M,<character>,<move>,<move>,...": what it can do (sent when the director connects).
  int moves(char* b, int n, const Character& c) const {
    int k = snprintf(b, n, "M,%s", c.name);
    for (int i = 0; i < c.choreo.moveCount && k < n - 1; i++) k += snprintf(b + k, n - k, ",%s", c.moveNames[i]);
    return k;
  }

  // Returns true (and fills b) when a summary is due.
  bool summary(char* b, int n, const DollPet& pet, uint32_t now) {
    if (now - lastSummary_ < SUMMARY_MS) return false;
    static const char* const MOODS[] = {"Asleep", "Curious", "IntoIt", "Hyped"};
    float silence = heard_ ? (now - lastSound_) / 1000.0f : -1;
    snprintf(b, n,
             "S,{\"t\":%u,\"character\":\"%s\",\"mood\":\"%s\",\"energy\":%.2f,\"intent\":\"%s\",\"thought\":\"%s\","
             "\"familiarity\":%.2f,\"silence_s\":%.1f,\"notes\":%d,\"hits\":%d,\"played_s\":%u}",
             (unsigned)now, pet.character().name, MOODS[(int)pet.mood.mood()], pet.mood.energy(),
             intentName(pet.mind.intent()), pet.mind.thought(), pet.bond.familiarity(), silence, notes_, hits_,
             (unsigned)pet.bond.memory().playSeconds);
    lastSummary_ = now;
    notes_ = hits_ = 0;
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
  uint32_t lastSummary_ = 0, lastSound_ = 0;
  int      notes_ = 0, hits_ = 0;
  bool     heard_ = false;
};
