#!/bin/sh
# Render a paper-doll character's parts, ink them, compile its moves, and
# regenerate its pack in src/gen/chars/<character>/ (the firmware includes every pack).
#   tools/build_doll.sh <character>        e.g. tools/build_doll.sh jay
set -e
cd "$(dirname "$0")/.."
CHAR=${1:?usage: tools/build_doll.sh <character>}
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
WORK=.pio/art/${CHAR}doll
DOLL=art/${CHAR}_doll
rm -rf "$WORK/raw"
"$BLENDER" -b -P "art/blender/${CHAR}_doll.py" -- "$WORK" 2>&1 | grep -E "^rendered|Error|Traceback|line [0-9]+" || true
rm -rf "$DOLL/poses"
mkdir -p "$DOLL"
uv run -q tools/ink.py "$WORK/raw" "$DOLL/poses" --palette "$WORK/parts.json"
cp "$WORK/parts.json" "$DOLL/parts.json"
uv run -q tools/build_doll.py "$DOLL" "$CHAR"
python3 tools/build_moves.py "art/blender/${CHAR}_moves.py" "$DOLL/parts.json" "$CHAR"
