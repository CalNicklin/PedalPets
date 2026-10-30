#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyserial", "anthropic"]
# ///
"""The director: a slow, optional mind for the pet, running on this computer.

Usage:
  uv run tools/director.py [--backend rules|claude] [--keys n4] [--seconds 120] [--log run.jsonl] [--port ...]

Turns on the board's director mode (`g`), then for every summary the board
sends ("S,{json}" every 6 s, and at once on a moment: a hit, waking, the music
stopping) decides whether to suggest anything, and sends it back as one
"#D ..." line (see src/core/directive.h). It speaks sparingly: at most every
QUIET_S seconds, except at moments. The pet runs fine on its own; this only
adds a layer of character on top, and never blocks it.

Every run is logged (--log, default .pio/director/<time>.jsonl): the prompt,
each summary, each raw reply, what was sent after checking, and what the board
applied. tools/director_page.py turns a log into a readable page.

Backends:
  rules   offline heuristics (free; for testing the loop)
  claude  a fast Claude model (spends API credits). The key comes from
          ANTHROPIC_API_KEY, or from the file ~/.config/pedalpets/anthropic_key
          (create it yourself, chmod 600; keep keys out of shell profiles).
"""

import argparse
import json
import os
import random
import re
import sys
import threading
import time

INTENTS = ["None", "Watch", "Bored", "WantsYou", "Investigate"]
SUGGESTIBLE = ["Bored", "WantsYou"]   # the others come from what it sees (a leaf); only while it's quiet
THOUGHT_MAX = 39
QUIET_S = 18
MODEL = "claude-haiku-4-5"
KEY_FILE = os.path.expanduser("~/.config/pedalpets/anthropic_key")


def to_line(d, moves, mood=None):
    """A suggestion dict -> a safe "#D ..." line (or None if there's nothing to say).
    Intents only while it's quiet (Curious), and only the ones it can't see for itself."""
    if not d:
        return None
    parts = []
    intent = d.get("intent")
    if intent in SUGGESTIBLE and mood in (None, "Curious"):
        parts.append(f"intent={intent}")
    for_s = d.get("for_s")
    if isinstance(for_s, (int, float)):
        parts.append(f"for={int(max(2, min(30, for_s)) * 1000)}")
    move = d.get("move")
    if move in moves:
        parts.append(f"move={move}")
    if d.get("look") == "you":
        parts.append("look=you")
    thought = d.get("thought")
    if isinstance(thought, str) and thought.strip():
        clean = re.sub(r"[,;\"\\\n\r]", " ", thought).strip()[:THOUGHT_MAX]
        parts.append(f"thought={clean}")
    return "#D " + ";".join(parts) if parts else None


class Rules:
    """Offline director: a few character beats on top of the pet's own life."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.quiet_said = False

    def decide(self, s, moves):
        say = self.rng.choice
        if s["mood"] == "Asleep":
            return {}
        if s["hits"] >= 2:
            return {"thought": say(["whoa - easy!", "that one rattled me", "ow my ears!"]), "for_s": 4}
        if s["mood"] == "Hyped" and s["notes"] > 15:
            return {"thought": say(["this is the one!", "don't stop!", "louder!"]), "for_s": 5}
        if s["mood"] == "Curious" and 8 < s["silence_s"] < 25 and s["familiarity"] > 0.3 and not self.quiet_said:
            self.quiet_said = True
            wave = next((m for m in ("wave", "beckon", "hop_small") if m in moves), None)
            return {"intent": "WantsYou", "for_s": 6, "move": wave, "look": "you",
                    "thought": say(["play that riff again?", "more please!", "is that it?"])}
        if s["silence_s"] < 2:
            self.quiet_said = False
        return {}


class Claude:
    """A fast Claude model as the pet's inner voice. Calls run in a thread; a
    summary that arrives while one is in flight is skipped (never queued)."""

    SYSTEM = (
        "You are the inner voice of {character}, a small animated pet living on the screen of a guitar "
        "effects pedal. It already reacts to the guitarist's playing on its own (dancing, startling, "
        "sleeping, getting bored); you only add a little character on top.\n"
        "You get a JSON summary every few seconds, and straight away when something happens ('moment': "
        "big hit, cut, woke up, music stopped, mood changed). Fields: mood (Asleep, Curious = quiet, "
        "IntoIt = grooving, Hyped), energy 0..1, its own intent and thought right now, familiarity with "
        "the player 0..1 (a stranger .. an old friend), seconds of silence, notes and hits since the last "
        "summary.\n"
        "Reply with ONE line of JSON and nothing else. Usually reply {{}}: stay quiet unless you have "
        "something that really adds to the moment - a reaction to a moment, a comment on the playing, "
        "missing the player in a long silence, recognising an old friend. At most one line in three.\n"
        'Otherwise any of {{"thought": first person, under 38 characters, no commas, "move": one of its '
        'moves or null, "look": "you" or null, "intent": "Bored" or "WantsYou" (only when mood is Curious), '
        '"for_s": 3..15}}.\n'
        "Its moves: {moves}.\nStay in character, be playful, never repeat a thought, and don't narrate "
        "what it's already doing."
    )

    def __init__(self, character, moves):
        import anthropic
        self.client = anthropic.Anthropic()
        self.system = self.SYSTEM.format(character=character, intents=INTENTS, moves=", ".join(moves))
        self.history = []
        self.busy = threading.Lock()

    def decide_async(self, s, moves, send, log):
        if not self.busy.acquire(blocking=False):
            log({"type": "skipped", "t": s["t"], "why": "still thinking about the last one"})
            return False
        started = time.time()

        def run():
            try:
                self.history = (self.history + [{"role": "user", "content": json.dumps(s)}])[-8:]
                msg = self.client.messages.create(model=MODEL, max_tokens=120, system=self.system,
                                                  messages=self.history, timeout=8)
                text = msg.content[0].text.strip()
                self.history.append({"role": "assistant", "content": text})
                log({"type": "reply", "t": s["t"], "raw": text, "ms": int((time.time() - started) * 1000),
                     "tokens": {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}})
                try:
                    d = json.loads(text[text.index("{"):text.rindex("}") + 1])
                except ValueError:
                    d = {}
                send(d, s)
            except Exception as e:  # network trouble: the pet carries on regardless
                log({"type": "error", "t": s["t"], "error": str(e)})
                print(f"director: {e}", file=sys.stderr)
            finally:
                self.busy.release()
        threading.Thread(target=run, daemon=True).start()
        return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/cu.usbserial-10")
    ap.add_argument("--backend", choices=["rules", "claude"], default="rules")
    ap.add_argument("--keys", default="", help="keys to send after director mode is on (e.g. n4)")
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--log", help="JSONL log of the run (default .pio/director/<time>.jsonl)")
    a = ap.parse_args()
    if a.backend == "claude" and not os.environ.get("ANTHROPIC_API_KEY"):
        if not os.path.exists(KEY_FILE):
            sys.exit(f"director: the claude backend needs ANTHROPIC_API_KEY or {KEY_FILE}")
        os.environ["ANTHROPIC_API_KEY"] = open(KEY_FILE).read().strip()

    log_path = a.log or os.path.join(".pio", "director", time.strftime("%Y%m%d-%H%M%S") + ".jsonl")
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    log_file = open(log_path, "w")
    lock = threading.Lock()

    def log(entry):
        with lock:
            log_file.write(json.dumps(entry) + "\n")
            log_file.flush()

    import serial
    port = serial.Serial()
    port.port, port.baudrate, port.timeout = a.port, 115200, 0.2
    port.dtr = port.rts = False
    port.open()
    buf, t0 = b"", time.time()
    while b"ready" not in buf and time.time() - t0 < 8:
        buf += port.read(256)
    port.write(b"g" + a.keys.encode())

    state = {"moves": [], "character": "the pet", "last_said": -1e9}

    def send(d, summary):
        line = to_line(d, state["moves"], summary.get("mood"))
        log({"type": "sent" if line else "quiet", "t": summary["t"], "line": line})
        if line:
            state["last_said"] = summary["t"] / 1000
            with lock:
                port.write((line + "\n").encode())
            print(f"  -> {line}")

    backend = Rules() if a.backend == "rules" else None
    log({"type": "start", "backend": a.backend, "model": MODEL if a.backend == "claude" else None,
         "keys": a.keys, "quiet_s": QUIET_S})
    pending, t0 = b"", time.time()
    while time.time() - t0 < a.seconds:
        pending += port.read(4096)
        *lines, pending = pending.split(b"\n")
        for raw in lines:
            line = raw.decode(errors="replace").strip()
            if line.startswith("M,"):
                state["character"], *state["moves"] = line[2:].split(",")
                print(f"director: {state['character']}, {len(state['moves'])} gestures ({a.backend})")
                if a.backend == "claude":
                    backend = Claude(state["character"], state["moves"])
                    log({"type": "prompt", "character": state["character"], "system": backend.system})
            elif line.startswith("S,"):
                try:
                    summary = json.loads(line[2:])
                except ValueError:
                    continue
                log({"type": "summary", **summary})
                moment = summary.get("moment") or ""
                print(f"{summary['t'] / 1000:7.1f}s  {summary['mood']:<7} {moment:<13} {summary['thought']}")
                # Speak sparingly: at moments, or when it's been quiet a while.
                if not moment and summary["t"] / 1000 - state["last_said"] < QUIET_S:
                    log({"type": "skipped", "t": summary["t"], "why": f"said something < {QUIET_S} s ago"})
                    continue
                if isinstance(backend, Rules):
                    send(backend.decide(summary, state["moves"]), summary)
                elif backend:
                    backend.decide_async(summary, state["moves"], send, log)
            elif line.startswith("directed:"):
                log({"type": "applied", "line": line[len("directed: "):]})
                print(f"  ok {line[len('directed: '):]}")
    port.write(b"g")
    port.close()
    log_file.close()
    print(f"director: log in {log_path}")


if __name__ == "__main__":
    main()
