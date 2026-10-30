#!/usr/bin/env python3
"""Turn a director log (tools/director.py --log run.jsonl) into a readable page.

Usage:  python3 tools/director_page.py run.jsonl out.html

Two voices side by side, moment by moment: what the board reported (its mood,
what just happened, the pet's own thought) and what the director did about it
(asked or held back, the raw reply, what was sent after checking, whether the
board applied it). The prompt the model was given is at the top. The page
itself groups the raw log entries, so tools/director.py --serve uses the same
page live, with controls to start a round.
"""

import json
import sys
from pathlib import Path


def entries_from(log):
    return [json.loads(line) for line in log.splitlines() if line.strip()]


def render(data, template):
    payload = json.dumps(data).replace("</", "<\\/")
    return template.replace("/*DATA*/null", payload)


def main():
    entries = entries_from(Path(sys.argv[1]).read_text())
    data = {"entries": entries, "name": Path(sys.argv[1]).stem, "live": False}
    template = (Path(__file__).parent / "director_page.html").read_text()
    Path(sys.argv[2]).write_text(render(data, template))
    print(f"director_page: {sum(e['type'] == 'summary' for e in entries)} moments -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
