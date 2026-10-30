#pragma once
// Fitting a spoken line into the caption: one line of up to SPEECH_LINE
// characters (the display's 6 px font across nearly the full width), or two,
// broken between words; a line too long for two ends in "..".
constexpr int SPEECH_LINE = 24;

int wrapSpeech(const char* text, char lines[2][SPEECH_LINE + 1]);   // returns the line count (0..2)
