#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyserial"]
# ///
"""Record the board's per-frame telemetry to a timeline CSV.

Usage:  uv run tools/capture_device.py out.csv --keys d1 --seconds 90

Opening the port may reboot the board; the script waits for the "ready"
banner, turns telemetry on (`t`), sends --keys, then records `T,...` lines.
"""

import argparse
import time

import serial

HEADER = "t_ms,pose,eye,mood,energy,reaction,step,frame_us"   # clip packs ("T," lines)


def doll_header(n_parts):
    """Paper-doll packs ("D," lines)."""
    return ("t_ms,mood,energy,reaction,frame_us,flip" + "".join(f",p{i}_img,p{i}_x,p{i}_y" for i in range(n_parts))
            + "".join(f",m{i}_img,m{i}_x,m{i}_y" for i in range(MARKS)))


MARKS = 3   # CHOREO_MAX_MARKS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--port", default="/dev/cu.usbserial-10")
    ap.add_argument("--keys", default="1")
    ap.add_argument("--seconds", type=float, default=90)
    a = ap.parse_args()

    s = serial.Serial()
    s.port, s.baudrate, s.timeout = a.port, 115200, 0.2
    s.dtr = s.rts = False
    s.open()
    buf, t = b"", time.time()
    while b"ready" not in buf and time.time() - t < 3:
        buf += s.read(256)
    time.sleep(0.3)
    s.reset_input_buffer()
    s.write(b"r")
    time.sleep(0.3)
    s.write(b"t" + a.keys.encode())

    rows, line, t = [], b"", time.time()
    header_line = None
    while time.time() - t < a.seconds:
        line += s.read(4096)
        *done, line = line.split(b"\n")
        for d in done:
            if d.startswith(b"H,"):
                header_line = d.decode(errors="replace").strip()[2:]
        rows += [d.decode(errors="replace").strip() for d in done if d[:2] in (b"T,", b"D,")]
    s.write(b"t")
    doll = rows and rows[0].startswith("D,")
    rows = [r[2:] for r in rows]
    header = header_line if doll and header_line else (doll_header((rows[0].count(",") - 5) // 3 - MARKS)
                                                      if doll else HEADER)
    with open(a.out, "w") as f:
        f.write(header + "\n" + "\n".join(rows) + "\n")
    print(f"wrote {a.out} ({len(rows)} frames)")


if __name__ == "__main__":
    main()
