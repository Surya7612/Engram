#!/usr/bin/env bash
# Build EngramCompanion.app into companion/macos/dist/ (ad-hoc signed).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
APP="$DIST/EngramCompanion.app"
BIN_NAME="EngramCompanion"

cd "$ROOT"
echo "==> swift build -c release"
swift build -c release

BIN="$(swift build -c release --show-bin-path)/$BIN_NAME"
if [[ ! -x "$BIN" ]]; then
  echo "error: binary not found at $BIN" >&2
  exit 1
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cp "$BIN" "$APP/Contents/MacOS/$BIN_NAME"
chmod +x "$APP/Contents/MacOS/$BIN_NAME"
cp "$ROOT/Info.plist" "$APP/Contents/Info.plist"

# Bundle SPM resource bundle if present (fixture text).
RES_BUNDLE="$(dirname "$BIN")/${BIN_NAME}_${BIN_NAME}.bundle"
if [[ -d "$RES_BUNDLE" ]]; then
  cp -R "$RES_BUNDLE" "$APP/Contents/Resources/"
fi

# Ad-hoc sign (Gatekeeper will still warn until notarized).
codesign --force --deep --sign - "$APP"
codesign --verify --verbose=2 "$APP" || true

echo "==> Built $APP"
echo "    Open once via right-click → Open if Gatekeeper blocks ad-hoc builds."
