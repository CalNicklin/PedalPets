#include "directive.h"
#include <stdlib.h>
#include <string.h>

namespace {

// Copies field `key` (up to ';' or the end) into buf; false if absent.
bool field(const char* line, const char* key, char* buf, int size) {
  size_t k = strlen(key);
  for (const char* p = line; (p = strstr(p, key)); p++) {
    if ((p != line && p[-1] != ' ' && p[-1] != ';') || p[k] != '=') continue;
    const char* v = p + k + 1;
    int n = 0;
    while (v[n] && v[n] != ';' && v[n] != '\n' && v[n] != '\r' && n < size - 1) {
      char c = v[n];
      buf[n] = c == ',' ? ' ' : (c == '"' || c == '\\') ? '\'' : c;   // thoughts go into CSV and JSON lines
      n++;
    }
    buf[n] = 0;
    return true;
  }
  return false;
}
}  // namespace

bool parseDirective(const char* line, int (*lookupMove)(const char*), Directive* out) {
  if (strncmp(line, "#D", 2) != 0) return false;
  *out = Directive();
  char buf[64];
  if (field(line, "intent", buf, sizeof(buf)))
    for (int i = 0; i < INTENT_COUNT; i++)
      if (!strcmp(buf, intentName((Intent)i))) out->intent = (Intent)i;
  if (field(line, "for", buf, sizeof(buf))) {
    long ms = strtol(buf, nullptr, 10);
    if (ms > 0 && ms <= 60000) out->forMs = (uint32_t)ms;
  }
  if (field(line, "move", buf, sizeof(buf)) && lookupMove) out->move = lookupMove(buf);
  if (field(line, "look", buf, sizeof(buf))) out->lookAtYou = !strcmp(buf, "you");
  field(line, "thought", out->thought, DIRECTIVE_THOUGHT);
  return true;
}
