#pragma once
#include <stdint.h>
#include "intent.h"

// A suggestion from the director (a slow, optional mind outside the device:
// a rules script or an LLM on the host). It only nudges: an intent for a
// while, a move from the character's vocabulary, a look at you, a thought to
// show. The pet works fully without it; music reactions stay instant and local.
//
// Wire format, one line:  #D intent=WantsYou;for=8000;move=wave;look=you;thought=play that again?

constexpr int DIRECTIVE_THOUGHT = 40;

struct Directive {
  Intent   intent = Intent::None;     // None = leave its own wants alone
  uint32_t forMs = 6000;
  int      move = -1;                 // index into the character's moves, or -1
  bool     lookAtYou = false;
  char     thought[DIRECTIVE_THOUGHT] = {};
};

// lookupMove(name) -> move index or -1. Returns false if the line isn't a directive.
bool parseDirective(const char* line, int (*lookupMove)(const char*), Directive* out);
