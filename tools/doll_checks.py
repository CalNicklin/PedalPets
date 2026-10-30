#!/usr/bin/env python3
"""Animation-principle checks on a simulator channel dump.

Usage:
  PEDALPETS_CHANNELS=1 .pio/build/sim/program "1@100" 85000 7 > run.csv
  python3 tools/doll_checks.py run.csv

Each check reads the choreographer's raw channels (hop, legs, squash, x,
face) frame by frame and lists the moments that break a principle:
  anticipation  every take-off is preceded by a crouch
  landing       every touch-down squashes
  contact       feet don't slide while on the ground
  turns         facing flips happen in the air, never on the ground
"""

import re
import sys

GROUND = 0.5          # hop below this (pixels) counts as on the ground
AIRBORNE = 2.0        # hop above this counts as a jump
CROUCH = 0.4          # legs bend that reads as a crouch
SQUASH = 0.4          # squash (or legs bend) that reads as a landing
SLIDE = 0.25          # stage x moving this much per frame on the ground is a slide
LOOKBACK = 6          # frames before a take-off to look for the crouch
LANDING_WINDOW = 3    # frames after touch-down to look for the squash

_CH = re.compile(r"([a-zA-Z]\w*)=(-?[\d.]+)")


def parse(line):
    f = line.split(",")
    r = {"t": int(f[0]), "mood": int(f[1]), "reaction": f[3]}
    r.update({k: float(v) for k, v in _CH.findall(line)})
    return r


def load(path):
    with open(path) as f:
        next(f)
        return [parse(l) for l in f if "=" in l]


def takeoffs_without_anticipation(rows):
    bad = []
    for i in range(1, len(rows)):
        if rows[i - 1]["hop"] <= GROUND < rows[i]["hop"]:
            # find where it actually gets airborne, then look back from the lift-off
            before = rows[max(0, i - LOOKBACK):i]
            if not any(max(r["legs"], r["squash"]) >= CROUCH for r in before):
                if any(r["hop"] > AIRBORNE for r in rows[i:i + 8]):
                    bad.append(rows[i])
    return bad


def landings_without_squash(rows):
    bad = []
    for i in range(1, len(rows)):
        if rows[i - 1]["hop"] > GROUND >= rows[i]["hop"]:
            if not any(r["hop"] > AIRBORNE for r in rows[max(0, i - 8):i]):
                continue
            after = rows[i:i + LANDING_WINDOW + 1]
            if not any(max(r["squash"], r["legs"]) >= SQUASH for r in after):
                bad.append(rows[i])
    return bad


def foot_slides(rows):
    return [b for a, b in zip(rows, rows[1:])
            if a["hop"] < GROUND and b["hop"] < GROUND and abs(b["x"] - a["x"]) > SLIDE]


def ground_turns(rows):
    return [b for a, b in zip(rows, rows[1:]) if a["face"] != b["face"] and max(a["hop"], b["hop"]) < AIRBORNE]


CHECKS = [
    ("anticipation (take-offs with no crouch)", takeoffs_without_anticipation),
    ("landing (touch-downs with no squash)", landings_without_squash),
    ("contact (frames sliding on the ground)", foot_slides),
    ("turns (facing flips on the ground)", ground_turns),
]


def main():
    rows = load(sys.argv[1])
    failed = 0
    for name, check in CHECKS:
        bad = check(rows)
        failed += len(bad)
        print(f"{name}: {len(bad)}")
        for r in bad[:5]:
            print(f"    {r['t']:>6} ms  ({r['reaction']})")
    print(f"total: {failed}")


if __name__ == "__main__":
    main()
