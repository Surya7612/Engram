#!/usr/bin/env bash
# Package EngramCompanion.app into a drag-to-Applications DMG.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
APP="$DIST/EngramCompanion.app"
VERSION="${ENGRAM_COMPANION_VERSION:-0.5.0}"
DMG_NAME="EngramCompanion-${VERSION}.dmg"
DMG="$DIST/$DMG_NAME"
STAGE="$DIST/dmg-stage"

if [[ ! -d "$APP" ]]; then
  echo "==> App missing; running build-app.sh first"
  "$ROOT/scripts/build-app.sh"
fi

rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

# Prefer create-dmg when installed; else hdiutil.
if command -v create-dmg >/dev/null 2>&1; then
  create-dmg \
    --volname "Engram Companion" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "EngramCompanion.app" 150 180 \
    --app-drop-link 450 180 \
    "$DMG" \
    "$STAGE"
else
  hdiutil create \
    -volname "Engram Companion" \
    -srcfolder "$STAGE" \
    -ov \
    -format UDZO \
    "$DMG"
fi

rm -rf "$STAGE"
echo "==> DMG ready: $DMG"
echo "    Recruiter flow: open DMG → drag to Applications → grant Screen Recording → Capture & ask"
