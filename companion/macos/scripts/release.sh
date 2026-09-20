#!/usr/bin/env bash
# Optional: build DMG and upload to a GitHub Release.
# Usage: ./scripts/release.sh [tag]
# Requires: gh auth, network. Does not notarize (ad-hoc only).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../.." && pwd)"
VERSION="${ENGRAM_COMPANION_VERSION:-0.5.0}"
TAG="${1:-companion-v${VERSION}}"
DMG="$ROOT/dist/EngramCompanion-${VERSION}.dmg"

"$ROOT/scripts/build-app.sh"
"$ROOT/scripts/make-dmg.sh"

cd "$REPO_ROOT"
if ! gh release view "$TAG" >/dev/null 2>&1; then
  gh release create "$TAG" "$DMG" \
    --title "Engram Companion ${VERSION}" \
    --notes "$(cat <<EOF
macOS on-call companion (ad-hoc signed).

1. Download the DMG and drag **Engram Companion** to Applications
2. Right-click → Open the first time (ad-hoc / Gatekeeper)
3. Grant **Screen Recording** when prompted
4. **Capture window & ask** (API defaults to https://engram-cjph.onrender.com)

Browser alternative (any OS): https://engram-cjph.onrender.com/try → On-call situation

Notarized builds come later with Apple Developer credentials.
EOF
)"
else
  gh release upload "$TAG" "$DMG" --clobber
fi

echo "==> Uploaded $DMG to release $TAG"
