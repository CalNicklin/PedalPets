#!/usr/bin/env python3
"""Print the story of a paper-doll run: what the pet felt, did and thought.

Usage:  python3 tools/doll_story.py timeline.csv     (simulator or device telemetry)

One line whenever the mood, the reaction or the Mind's thought changes, so a
stretch of a run reads as a little story with reasons. Use it to review the
inner life (docs/superpowers/specs/2026-10-30-inner-life-design.md).
"""

import csv
import sys

MOODS = ["Asleep", "Curious", "IntoIt", "Hyped"]


def story(rows):
    out, last = [], None
    t0 = int(rows[0]["t_ms"]) if rows else 0
    for r in rows:
        key = (r["mood"], r["reaction"], r.get("thought", "-"))
        if key != last:
            rx = "" if r["reaction"] in ("-", "") else f"[{r['reaction']}] "
            out.append(f"{(int(r['t_ms']) - t0) / 1000:7.2f}s  {MOODS[int(r['mood'])]:<7}  {rx}{key[2]}")
            last = key
    return out


def main():
    with open(sys.argv[1]) as f:
        rows = list(csv.DictReader(f))
    print("\n".join(story(rows)))


if __name__ == "__main__":
    main()
