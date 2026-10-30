#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyserial", "anthropic"]
# ///
"""The director: a slow, optional mind for the pet, running on this computer.

Usage:
  uv run tools/director.py [--backend rules|claude] [--keys n4] [--seconds 120] [--port ...]

Turns on the board's director mode (`g`), then for every summary the board
sends ("S,{json}" every 6 s) decides whether to suggest anything, and sends it
back as one "#D ..." line (see src/core/directive.h). The pet runs fine on its
own; this only adds a layer of character on top, and never blocks it.

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
THOUGHT_MAX = 39
MODEL = "claude-haiku-4-5"
KEY_FILE = os.path.expanduser("~/.config/pedalpets/anthropic_key")


def to_line(d, moves):
    """A suggestion dict -> a safe "#D ..." line (or None if there's nothing to say)."""
    if not d:
        return None
    parts = []
    intent = d.get("intent")
    if intent in INTENTS and intent != "None":
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
        "effects pedal. It reacts to the guitarist's playing on its own (dancing, startling, sleeping); you "
        "only add character on top, sparingly. Every few seconds you get a JSON summary: mood (Asleep, "
        "Curious, IntoIt, Hyped), energy 0..1, its current intent and thought, familiarity with the player "
        "0..1 (a stranger .. an old friend), seconds of silence, notes and hits in the last 6 s.\n"
        "Reply with ONE line of JSON and nothing else: {{}} to stay quiet (most of the time), or any of "
        '{{"intent": one of {intents}, "for_s": 3..15, "move": one of its moves or null, "look": "you" or null, '
        '"thought": a short first-person thought, under 38 characters, no commas}}.\n'
        "Its moves: {moves}.\nBe playful and in character; comment on the playing, the silence, how well it "
        "knows the player. Don't repeat yourself; don't speak every time."
    )

    def __init__(self, character, moves):
        import anthropic
        self.client = anthropic.Anthropic()
        self.system = self.SYSTEM.format(character=character, intents=INTENTS, moves=", ".join(moves))
        self.history = []
        self.busy = threading.Lock()

    def decide_async(self, s, moves, send):
        if not self.busy.acquire(blocking=False):
            return False
        def run():
            try:
                self.history = (self.history + [{"role": "user", "content": json.dumps(s)}])[-8:]
                msg = self.client.messages.create(model=MODEL, max_tokens=120, system=self.system,
                                                  messages=self.history, timeout=8)
                text = msg.content[0].text.strip()
                self.history.append({"role": "assistant", "content": text})
                try:
                    d = json.loads(text[text.index("{"):text.rindex("}") + 1])
                except ValueError:
                    d = {}
                send(d)
            except Exception as e:  # network trouble: the pet carries on regardless
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
    a = ap.parse_args()
    if a.backend == "claude" and not os.environ.get("ANTHROPIC_API_KEY"):
        if not os.path.exists(KEY_FILE):
            sys.exit(f"director: the claude backend needs ANTHROPIC_API_KEY or {KEY_FILE}")
        os.environ["ANTHROPIC_API_KEY"] = open(KEY_FILE).read().strip()

    import serial
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = a.port, 115200, 0.2
    s.dtr = s.rts = False
    s.open()
    buf, t0 = b"", time.time()
    while b"ready" not in buf and time.time() - t0 < 8:
        buf += s.read(256)
    s.write(b"g" + a.keys.encode())
    lock = threading.Lock()

    def send(d):
        line = to_line(d, moves)
        if line:
            with lock:
                s.write((line + "\n").encode())
            print(f"  -> {line}")

    moves, character = [], "the pet"
    backend = Rules() if a.backend == "rules" else None
    pending, t0 = b"", time.time()
    while time.time() - t0 < a.seconds:
        pending += s.read(4096)
        *lines, pending = pending.split(b"\n")
        for raw in lines:
            line = raw.decode(errors="replace").strip()
            if line.startswith("M,"):
                character, *moves = line[2:].split(",")
                print(f"director: {character}, {len(moves)} moves ({a.backend})")
                if a.backend == "claude":
                    backend = Claude(character, moves)
            elif line.startswith("S,"):
                try:
                    summary = json.loads(line[2:])
                except ValueError:
                    continue
                print(f"{summary['t'] / 1000:7.1f}s  {summary['mood']:<7} {summary['thought']}")
                if isinstance(backend, Rules):
                    send(backend.decide(summary, moves))
                elif backend:
                    backend.decide_async(summary, moves, send)
            elif line.startswith("directed:"):
                print(f"  ok {line[len('directed: '):]}")
    s.write(b"g")
    s.close()


if __name__ == "__main__":
    main()
