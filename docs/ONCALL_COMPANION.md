# On-call companion (screen → context engine)

Narrow client for **operational situations**: ephemeral screen/OCR text → resolve service → grounded Engram answer with provenance.

This is **not** Microsoft Copilot Vision, WalkMe, or generic “AI that sees your desktop.” Engram remains the context engine; the companion is one runtime client (alongside IDE / Try / API).

## Recruiter paths

| Path | Who |
|---|---|
| [Hosted Try → On-call](https://engram-cjph.onrender.com/try#oncall) | Any browser — load fixture → Ask situation |
| [Mac companion DMG](https://github.com/Surya7612/Engram/releases) | Mac — drag to Applications → Screen Recording → Capture & ask |
| CLI / local API | Builders |

Capture is **explicit and user-initiated** only. Screen pixels stay on-device; only redacted text is sent once to `POST /situation` and is **not stored**.

## Demo script (browser)

1. Open https://engram-cjph.onrender.com/try#oncall  
2. **Load payment-worker fixture** (or paste) → **Ask situation**  
3. Expect **Payments Service**, evidence around INC-1842 / PR-8831 / ADR-62  

## Demo script (Mac companion + fake Datadog)

1. Download DMG from Releases (or `companion/macos/scripts/make-dmg.sh`)  
2. Drag to Applications → grant Screen Recording  
3. Open [`website/fake-datadog.html`](../website/fake-datadog.html) (served at `/site/fake-datadog.html` when API is up)  
4. **Capture window & ask** (API defaults to hosted Engram)

## Demo script (CLI)

Locked path: [`DEMO.md`](./DEMO.md).

```bash
source .venv/bin/activate
python main.py seed
python main.py situation --fixture payment-worker
```

API:

```bash
curl -s https://engram-cjph.onrender.com/situation \
  -H 'Content-Type: application/json' \
  -d @- <<'EOF' | jq
{
  "screen_text": "payment-worker TimeoutException POST /settlements P95 latency",
  "question": "What's happening here? What should I check first?"
}
EOF
```

## Ephemeral policy

- Screen text is **query context only**.
- Obvious secrets (`sk-`, `ghp_`, bearer-like tokens) are redacted before retrieval.
- Engram does **not** append screen text to the graph, vectors, or outcome log.

## macOS app

See [`companion/macos/README.md`](../companion/macos/README.md) for Download, DMG build, and ad-hoc vs notarized notes.

## Scope (honest)

| In | Out |
|---|---|
| Fixture / paste / explicit capture + Vision OCR | Background always-on capture |
| Hosted `/try` on-call + Mac DMG (ad-hoc) | Notarized Gatekeeper-clean (later) |
| Service resolve + grounded answer | HIPAA/BAA, SSO, generic desktop AI |
| On-call / KT-shaped questions | Full agent worktrees on this path |
