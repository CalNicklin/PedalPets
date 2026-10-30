#pragma once
#include <stdint.h>

// What the pet wants right now (chosen by the Mind, acted out by the
// Choreographer's idle vocabulary). None = the mood's own vocabulary.
enum class Intent : uint8_t { None, Watch, Bored, WantsYou, Investigate };
constexpr int INTENT_COUNT = 5;
