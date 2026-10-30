#!/bin/sh
# Render the Blender pet, ink it, write its manifest and regenerate firmware headers.
#   tools/build_pet.sh [action ...]     (default: all actions)
set -e
cd "$(dirname "$0")/.."
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
rm -rf .pio/pet/raw
"$BLENDER" -b -P art/blender/pet.py -- .pio/pet "$@" 2>&1 | grep -E "^rendered|Error|Traceback" || true
rm -rf art/pet/poses
uv run -q tools/ink.py .pio/pet/raw art/pet/poses
python3 tools/pet_manifest.py .pio/pet/actions.json art/pet/poses art/pet/manifest.toml
uv run -q tools/build_art.py art/pet/manifest.toml
