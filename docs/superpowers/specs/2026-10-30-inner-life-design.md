# Inner Life — Design

Date: 2026-10-30
Status: approved direction ("yes, go for it")
Builds on: `2026-10-30-paper-doll-design.md`

## Why

The jay moves smoothly but reads as a dancer cycling a vocabulary: moves are
picked by mood and beat, so nothing he does is *about* anything. References
(Mini Maui's tattoo, real jays) feel alive because the character is always
paying attention to something, acts for reasons, notices before reacting,
has a relationship (with Maui; for us, with the player), and is physically
part of a world that responds to him. Not one technique: the whole.

## Idea

A `Mind` above the choreographer. It doesn't animate; it decides what the
jay is paying attention to and what he wants, and steers the choreographer:

- **Attention** — always a target: *you* (the player, out of the screen), a
  leaf he kicked fluttering down, a spot on the ground, or nothing much
  (glances about). Candidates have salience (novelty, motion, nearness);
  interest habituates, so attention moves on. The head snaps to the target
  (real jays turn the head in a frame, then hold it still) and tracks it.
  A target behind him, if interesting enough, makes him turn round.
- **Wants (drives)** — boredom (rises awake in silence), curiosity (spikes
  on novelty, decays), wanting your attention (rises after you stop
  playing). Excitement and sleepiness come from the existing mood energy.
  The strongest want picks an **intent**: Watch, Bored, WantsYou,
  Investigate, or none (the mood's vocabulary as now). Each intent has its
  own idle vocabulary (bored: pecks, preens, sighs, wanders; wants you: looks
  at you, hops to the front, crest flicks; investigate: hops to the leaf and
  pecks it).
- **Noticing** — a loud event after quiet first gets a double-take: head
  snaps to you, eyes wide, then (~0.2 s later) the reaction plays.
- **Thoughts** — every intent/attention change is a short phrase ("bored →
  looking at you", "a leaf! watching it"). Logged in telemetry, so any stretch
  of a run reads as a story with reasons. That log is how we verify it.

Music remains the main stimulus: playing feeds energy, beats and reactions
exactly as now; the Mind shapes everything around them.

## Runtime

- `core/mind.{h,cpp}` (hardware-free, unit tested): `onEvent` (may defer a
  loud event for the double-take), `tick(mood, energy, head x/y, facing,
  leaves, now)`, outputs: gaze (look, pitch, eyes, weight), intent, turn
  request, thought.
- Choreographer gains: `setGaze()` (head look/pitch blended over moves),
  `setIntent()` (idle picks from the intent's vocabulary), `requestTurn()`.
- Art data (`jay_moves.py`): `INTENTS` vocabularies, emitted with the moves.
- Telemetry/simulator: a `thought` column; `tools/doll_story.py` prints the
  story of a run (moods, reactions, thoughts) for review.

## Not now

Critter crowd, props (mushroom, tree), memory of the player across sessions,
LLM director — later layers on the same Mind.
