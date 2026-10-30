#!/usr/bin/env python3
"""Turn a director log (tools/director.py --log run.jsonl) into a readable page.

Usage:  python3 tools/director_page.py run.jsonl out.html

Two voices side by side, moment by moment: what the board reported (its mood,
what just happened, the pet's own thought) and what the director did about it
(asked or held back, the raw reply, what was sent after checking, whether the
board applied it). The prompt the model was given is at the top.
"""

import json
import statistics
import sys
from pathlib import Path


def rows_from(log):
    entries = [json.loads(line) for line in log.splitlines() if line.strip()]
    start = next((e for e in entries if e["type"] == "start"), {})
    prompts = [e for e in entries if e["type"] == "prompt"]
    applied = [e["line"] for e in entries if e["type"] == "applied"]
    by_t = {}
    rows = []
    for e in entries:
        if e["type"] == "summary":
            row = {"summary": e, "status": "regular check-in"}
            rows.append(row)
            by_t[e["t"]] = row
        elif e.get("t") in by_t:
            row = by_t[e["t"]]
            if e["type"] == "skipped":
                row["status"] = "held"
                row["why"] = e["why"]
            elif e["type"] == "reply":
                row["reply"] = e
                row["status"] = "asked"
            elif e["type"] == "sent":
                row["sent"] = e["line"]
                row["status"] = "spoke"
                row["applied"] = e["line"] in applied
            elif e["type"] == "quiet":
                row["status"] = "quiet" if row.get("reply") or start.get("backend") == "rules" else row["status"]
            elif e["type"] == "error":
                row["status"] = "error"
                row["why"] = e["error"]
    for r in rows:                              # rules backend: no reply entries, a decision is still made
        if r["status"] == "regular check-in" and start.get("backend") == "rules":
            r["status"] = "quiet"
    replies = [r["reply"] for r in rows if r.get("reply")]
    stats = {
        "summaries": len(rows),
        "asked": len(replies) if start.get("backend") == "claude" else sum(r["status"] in ("spoke", "quiet") for r in rows),
        "spoke": sum(r["status"] == "spoke" for r in rows),
        "quiet": sum(r["status"] == "quiet" for r in rows),
        "held": sum(r["status"] == "held" for r in rows),
        "median_ms": int(statistics.median([x["ms"] for x in replies])) if replies else None,
        "tokens_in": sum(x["tokens"]["in"] for x in replies),
        "tokens_out": sum(x["tokens"]["out"] for x in replies),
        "applied": sum(bool(r.get("applied")) for r in rows),
    }
    return {"start": start, "prompt": prompts[-1] if prompts else None, "rows": rows, "stats": stats}


def render(data, template):
    payload = json.dumps(data).replace("</", "<\\/")
    return template.replace("/*DATA*/null", payload)


def main():
    log = Path(sys.argv[1]).read_text()
    data = rows_from(log)
    data["name"] = Path(sys.argv[1]).stem
    template = (Path(__file__).parent / "director_page.html").read_text()
    Path(sys.argv[2]).write_text(render(data, template))
    s = data["stats"]
    print(f"director_page: {s['summaries']} moments, spoke {s['spoke']}, quiet {s['quiet']}, held back {s['held']}")


if __name__ == "__main__":
    main()
