#!/bin/sh
# Render a Blender character, ink it, write its manifest and regenerate the
# firmware headers (so the next firmware build shows that character).
#   tools/build_pet.sh <character> [action ...]    e.g. tools/build_pet.sh jay
set -e
cd "$(dirname "$0")/.."
CHAR=${1:?usage: tools/build_pet.sh <character> [action ...]}
shift
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
WORK=.pio/art/$CHAR
rm -rf "$WORK/raw"
"$BLENDER" -b -P "art/blender/$CHAR.py" -- "$WORK" "$@" 2>&1 | grep -E "^rendered|Error|Traceback|line [0-9]+" || true
rm -rf "art/$CHAR/poses"
uv run -q tools/ink.py "$WORK/raw" "art/$CHAR/poses" --palette "$WORK/actions.json"
python3 tools/pet_manifest.py "$WORK/actions.json" "art/$CHAR/poses" "art/$CHAR/manifest.toml"
uv run -q tools/build_art.py "art/$CHAR/manifest.toml"
