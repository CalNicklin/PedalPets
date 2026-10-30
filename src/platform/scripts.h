#pragma once
#include <stdint.h>

// A scripted timeline is a list of mock key presses. Each entry fires `key`
// `repeat` times, starting at t_ms and spaced every_ms apart. Entries run
// independently, so they may overlap.
struct ScriptEntry { uint32_t t_ms; char key; uint16_t repeat; uint16_t every_ms; };
struct Script      { const ScriptEntry* entries; uint8_t count; };

// 1: a ~60 s "set", a quiet spell (it misses you, gets bored), a sudden hit
// out of nowhere (double-take), a little more playing, then silence until it
// winds down to sleep (~30 s after it calms to Curious).
static const ScriptEntry SCRIPT_SET[] = {
  {    0, '0',  1,    0 },  // silence
  { 3000, 'p',  1,    0 },  // first note wakes it
  { 4000, '+',  2,    0 },  // level 0.2
  { 4000, 'p', 20,  500 },  // noodling
  {14000, '+',  3, 1000 },  // build to 0.5
  {14000, 'P', 24,  250 },  // dig in: beat-step idle
  {20000, '+',  4,  500 },  // up to 0.9 → Hyped
  {20000, 'f',  4,  600 },  // flurry (repeats extend it)
  {24000, 'h',  1,    0 },  // big hit
  {25000, 'P', 16,  250 },  // keep playing
  {29500, 'c',  1,    0 },  // cut
  {31000, 's',  1,    0 },  // sustain...
  {35000, 'S',  1,    0 },  // ...released
  {36000, 'w',  1,    0 },  // swell
  {36000, '+',  5,  600 },
  {39000, 'W',  1,    0 },  // swell peak
  {39500, '-',  6, 1000 },  // fade out
  {39500, 'p', 10,  800 },
  {48000, '0',  1,    0 },  // silence: misses you, then gets bored
  {72000, 'h',  1,    0 },  // out of nowhere: double-take, then the startle
  {73000, 'p',  6,  400 },
  {76000, '0',  1,    0 },  // silence until it sleeps
};

// 2: priority drill — hit, cut, flurry, hit-during-flurry.
static const ScriptEntry SCRIPT_PRIORITY[] = {
  {    0, 'p', 1,    0 },
  {    0, '+', 6,    0 },
  { 2000, 'h', 1,    0 },
  { 5000, 'c', 1,    0 },
  { 6000, '+', 6,    0 },
  { 8000, 'f', 3,  500 },
  { 8800, 'h', 1,    0 },
  {12000, 'c', 1,    0 },
};

// 3: hold drill — short sustain, long sustain, swell without peak.
static const ScriptEntry SCRIPT_HOLDS[] = {
  {    0, 'p', 1, 0 },
  { 2000, 's', 1, 0 },
  { 2300, 'S', 1, 0 },
  { 5000, 's', 1, 0 },
  { 9000, 'S', 1, 0 },
  {12000, 'w', 1, 0 },  // no peak: crouch caps at 5 s, then leaps anyway
};

// 4: a quiet life — woken, then left alone (a light note now and then keeps it
// awake): watch it wander, get bored, play with the leaves, lie about.
static const ScriptEntry SCRIPT_QUIET[] = {
  {    0, 'p', 1,     0 },
  {20000, 'p', 5, 20000 },
};

#define SCRIPT_LEN(a) (uint8_t)(sizeof(a) / sizeof(a[0]))
static const Script SCRIPTS[] = {
  {SCRIPT_SET,      SCRIPT_LEN(SCRIPT_SET)},
  {SCRIPT_PRIORITY, SCRIPT_LEN(SCRIPT_PRIORITY)},
  {SCRIPT_HOLDS,    SCRIPT_LEN(SCRIPT_HOLDS)},
  {SCRIPT_QUIET,    SCRIPT_LEN(SCRIPT_QUIET)},
};
constexpr int SCRIPT_COUNT = sizeof(SCRIPTS) / sizeof(SCRIPTS[0]);
