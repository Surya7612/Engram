# Engram Companion (macOS)

On-call client for Engram: **explicit** window/region capture → on-device Vision OCR → `POST /situation` → grounded answer with evidence.

Screen pixels stay on-device. Only redacted OCR text is sent once. Engram does **not** store screen text as permanent memory.

This is **not** Microsoft Copilot Vision or WalkMe. Capture is user-initiated only (no background recording).

## Download (recruiters)

1. Download the **EngramCompanion** DMG from [GitHub Releases](https://github.com/Surya7612/Engram/releases) (or build locally below).
2. Open the DMG → drag **Engram Companion** to Applications.
3. First launch: right-click → **Open** (ad-hoc signed builds are not notarized yet).
4. Grant **Screen Recording** in System Settings → Privacy & Security.
5. Launch → **Capture window & ask** (API already points at `https://engram-cjph.onrender.com`).

Optional browser path (any OS): [hosted Try → On-call situation](https://engram-cjph.onrender.com/try#oncall).

### Ad-hoc vs notarized

| Build | Gatekeeper |
|---|---|
| **Ad-hoc** (default scripts) | Right-click → Open once |
| **Notarized** (later) | Clean open when Apple Developer ID + `notarytool` are configured |

You do not need a Developer ID to build or demo locally.

## Build DMG locally

```bash
cd companion/macos
./scripts/build-app.sh    # → dist/EngramCompanion.app
./scripts/make-dmg.sh     # → dist/EngramCompanion-0.5.0.dmg
# optional upload:
# ./scripts/release.sh companion-v0.5.0
```

`dist/` is gitignored.

## Develop from source

- macOS 14+
- Xcode 15+ / Swift 5.9+

```bash
cd companion/macos
open Package.swift
# or: swift run EngramCompanion
```

Default API base in the app: **hosted** `https://engram-cjph.onrender.com` (change under Settings). Local builders: `http://127.0.0.1:8000` after `python main.py seed && python main.py serve`.

## Demo script (interview)

1. Open the [Fake Datadog](../../website/fake-datadog.html) page (or real Datadog).
2. Click **Capture window & ask** (or **Capture region & ask**, or ⌃⌥Space while Companion is focused).
3. Expect **Payments Service**, evidence around INC-1842 / PR-8831 / ADR-62.
4. Fallback without capture: **Use demo fixture**.

## Scope

| In | Out |
|---|---|
| Explicit window / region capture + Vision OCR | Background always-on capture |
| Hosted API by default | Electron / Windows port |
| Fixture / paste / browser `/try` on-call | Voice, wake word, phone capture |
