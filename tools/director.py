#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyserial", "anthropic"]
# ///
"""The director: a slow, optional mind for the pet, running on this computer.

Usage:
  uv run tools/director.py --serve                    a page on http://localhost:8765 to start rounds and watch them
  uv run tools/director.py [--backend rules|claude] [--character skeleton] [--scene graveyard]
                           [--seconds 105] [--log run.jsonl] [--port ...]

A round resets the board (asleep), picks the character and scene, turns on
director mode (`g`) and plays round 5 (woken, a set, silence, asleep, woken
again). For every summary the board
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
THOUGHT_MAX = 39   # the board shows up to two lines; the prompt asks for one (24)
QUIET_S = 18
MODEL = "claude-haiku-5-5"   # newest Haiku (checked with models.list, 2026-10-30)
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
        'Otherwise any of {{"thought": first person, under 24 characters (it shows on one line), "move": one of its '
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
                while self.history and self.history[0]["role"] != "user":   # must open with a summary
                    self.history.pop(0)
                # No extended thinking: Haiku 5.5 thinks by default, which spends the small
                # budget before it answers; this is a quick inner voice, not a puzzle.
                msg = self.client.messages.create(model=MODEL, max_tokens=120, system=self.system,
                                                  messages=self.history, thinking={"type": "disabled"},
                                                  timeout=8)
                text = "".join(b.text for b in msg.content if b.type == "text").strip()
                self.history.append({"role": "assistant", "content": text})
                log({"type": "reply", "t": s["t"], "raw": text, "ms": int((time.time() - started) * 1000),
                     "tokens": {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}})
                try:
                    d = json.loads(text[text.index("{"):text.rindex("}") + 1])
                except ValueError:
                    d = {}
                send(d, s)
            except Exception as e:  # network trouble: the pet carries on regardless
                if self.history and self.history[-1]["role"] == "user":
                    self.history.pop()                     # no answer: forget the question
                log({"type": "error", "t": s["t"], "error": str(e)})
                print(f"director: {e}", file=sys.stderr)
            finally:
                self.busy.release()
        threading.Thread(target=run, daemon=True).start()
        return True


def api_key():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        if not os.path.exists(KEY_FILE):
            raise RuntimeError(f"the claude director needs ANTHROPIC_API_KEY or {KEY_FILE}")
        os.environ["ANTHROPIC_API_KEY"] = open(KEY_FILE).read().strip()


def run_round(port_name, character, scene, backend_name, seconds, log, stop=lambda: False):
    """One round on the board: reset, pick the packs, director on, round 5, log it all."""
    import serial
    if backend_name == "claude":
        api_key()
    port = serial.Serial()
    port.port, port.baudrate, port.timeout = port_name, 115200, 0.2
    port.dtr = port.rts = False
    port.open()
    lock = threading.Lock()
    lines_in = []

    def read_lines(until, timeout=4.0):
        """Read lines until one matches until(line) (returns it) or the timeout."""
        pending, t0 = b"", time.time()
        while time.time() - t0 < timeout:
            pending += port.read(1024)
            *done, pending = pending.split(b"\n")
            for raw in done:
                line = raw.decode(errors="replace").strip()
                lines_in.append(line)
                if until(line):
                    return line
        return None

    def packs_line():
        return read_lines(lambda l: l.startswith("character:"))

    try:
        read_lines(lambda l: "ready" in l, 6)             # opening the port may reboot it
        port.write(b"G")                                   # director off while we set up
        port.write(b"r")                                   # asleep, fresh
        line = packs_line()
        for key, want, field in ((b"n", character, 1), (b"b", scene, 3)):
            for _ in range(4):
                if not line or not want or line.split()[field] == want:
                    break
                port.write(key)
                line = packs_line()
        if line and ((character and line.split()[1] != character) or (scene and line.split()[3] != scene)):
            raise RuntimeError(f"the board has no {character} / {scene} ({line})")

        state = {"moves": [], "character": character, "last_said": -1e9}

        def send(d, summary):
            out = to_line(d, state["moves"], summary.get("mood"))
            log({"type": "sent" if out else "quiet", "t": summary["t"], "line": out})
            if out:
                state["last_said"] = summary["t"] / 1000
                with lock:
                    port.write((out + "\n").encode())

        backend = Rules() if backend_name == "rules" else None
        log({"type": "start", "backend": backend_name, "model": MODEL if backend_name == "claude" else None,
             "character": character, "scene": scene, "quiet_s": QUIET_S})
        port.write(b"g5")                                  # director on, play the round
        pending, t0 = b"", time.time()
        while time.time() - t0 < seconds and not stop():
            pending += port.read(4096)
            *lines, pending = pending.split(b"\n")
            for raw in lines:
                line = raw.decode(errors="replace").strip()
                if line.startswith("M,"):
                    state["character"], *state["moves"] = line[2:].split(",")
                    if backend_name == "claude":
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
        log({"type": "end", "stopped": bool(stop())})
    finally:
        try:
            port.write(b"G0")                              # director off, music off
        finally:
            port.close()


def serve(port_name, http_port=8765):
    """A local page to start rounds and watch the director work, live."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import director_page

    page = director_page.render({"entries": [], "name": "", "live": True},
                                open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "director_page.html")).read())
    st = {"entries": [], "running": False, "started": 0.0, "duration": 105.0, "error": None, "stop": False}
    lock = threading.Lock()

    def start(character, scene, backend):
        with lock:
            if st["running"]:
                return "a round is already running"
            st.update(entries=[], running=True, started=time.time(), error=None, stop=False)
        path = os.path.join(".pio", "director", time.strftime("%Y%m%d-%H%M%S") + ".jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        f = open(path, "w")

        def log(entry):
            with lock:
                st["entries"].append(entry)
                f.write(json.dumps(entry) + "\n")
                f.flush()

        def go():
            try:
                run_round(port_name, character, scene, backend, st["duration"], log, lambda: st["stop"])
            except Exception as e:
                st["error"] = str(e)
                print(f"director: {e}", file=sys.stderr)
            finally:
                f.close()
                st["running"] = False
                print(f"director: log in {path}")
        threading.Thread(target=go, daemon=True).start()
        return None

    class Handler(BaseHTTPRequestHandler):
        def reply(self, body, kind="application/json"):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/":
                return self.reply(page, "text/html; charset=utf-8")
            if url.path == "/events":
                since = int(parse_qs(url.query).get("since", ["0"])[0])
                with lock:
                    reset = since > len(st["entries"])
                    new = st["entries"][0 if reset else since:]
                    return self.reply(json.dumps({"entries": new, "reset": reset, "running": st["running"],
                                                  "elapsed": time.time() - st["started"] if st["running"] else 0,
                                                  "duration": st["duration"], "error": st["error"]}))
            self.send_error(404)

        def do_POST(self):
            if self.path == "/start":
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                err = start(body.get("character"), body.get("scene"), body.get("backend", "claude"))
                return self.reply(json.dumps({"error": err}))
            if self.path == "/stop":
                st["stop"] = True
                return self.reply(json.dumps({"ok": True}))
            self.send_error(404)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", http_port), Handler)
    print(f"director: open http://localhost:{http_port}  (Ctrl+C to quit)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/cu.usbserial-10")
    ap.add_argument("--serve", action="store_true", help="a local page to start rounds and watch them")
    ap.add_argument("--http-port", type=int, default=8765)
    ap.add_argument("--backend", choices=["rules", "claude"], default="claude")
    ap.add_argument("--character", default="skeleton")
    ap.add_argument("--scene", default="graveyard")
    ap.add_argument("--seconds", type=float, default=105)
    ap.add_argument("--log", help="JSONL log of the run (default .pio/director/<time>.jsonl)")
    a = ap.parse_args()
    if a.serve:
        return serve(a.port, a.http_port)
    path = a.log or os.path.join(".pio", "director", time.strftime("%Y%m%d-%H%M%S") + ".jsonl")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        def log(entry):
            f.write(json.dumps(entry) + "\n")
            f.flush()
        try:
            run_round(a.port, a.character, a.scene, a.backend, a.seconds, log)
        except RuntimeError as e:
            sys.exit(f"director: {e}")
    print(f"director: log in {path}")


if __name__ == "__main__":
    main()
