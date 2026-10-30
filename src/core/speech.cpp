#include "speech.h"
#include <string.h>

int wrapSpeech(const char* text, char lines[2][SPEECH_LINE + 1]) {
  lines[0][0] = lines[1][0] = 0;
  if (!text) return 0;
  while (*text == ' ') text++;
  int n = 0;
  for (; n < 2 && *text; n++) {
    int len = (int)strlen(text);
    int take = len;
    if (len > SPEECH_LINE) {                       // break at the last space that fits
      take = SPEECH_LINE;
      for (int i = SPEECH_LINE; i > 0; i--)
        if (text[i] == ' ') { take = i; break; }
    }
    memcpy(lines[n], text, take);
    lines[n][take] = 0;
    while (take > 0 && lines[n][take - 1] == ' ') lines[n][--take] = 0;
    text += take;
    while (*text == ' ') text++;
  }
  if (*text && n == 2) {                           // more than fits: end on ".."
    int l = (int)strlen(lines[1]);
    if (l > SPEECH_LINE - 2) l = SPEECH_LINE - 2;
    lines[1][l] = lines[1][l + 1] = '.';
    lines[1][l + 2] = 0;
  }
  return n;
}
