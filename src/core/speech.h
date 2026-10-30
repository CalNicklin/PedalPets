#pragma once
// Fitting a spoken line into a speech bubble: up to two lines of SPEECH_LINE
// characters (the display's 6 px font: ~114 px), broken between words; a line
// too long for two ends in "..".
constexpr int SPEECH_LINE = 19;

int wrapSpeech(const char* text, char lines[2][SPEECH_LINE + 1]);   // returns the line count (0..2)
