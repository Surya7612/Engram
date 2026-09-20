# Engram demo script (alpha)

One reproducible path for interviews and self-serve Try. Nothing merges.

## Hosted (any browser) — ~3 minutes

URL: [https://engram-cjph.onrender.com/try](https://engram-cjph.onrender.com/try)

1. **Check API** if the free tier is waking up.

**Demo A — your GitHub**

2. **Ingest** the default public repo → named service in graph + vectors.
3. **Query** / **Preflight** → evidence about *that* repo.

**Demo B — seeded sample org** (not the repo you connected)

4. **On-call** → Load payment-worker fixture → **Ask situation**  
   Expect Payments Service + INC-1842 / PR-8831 / ADR-62.
5. **Auth — Run agents** on TTL task → expect `block` (ADR-12).
6. **Reject** → **Run agents** again → prior surfaces.

Public Try: no BYO clone/run, no browser PATs, no `/eval`.

## Mac companion (optional; not required for Try)

1. Build DMG: `cd companion/macos && ./scripts/build-app.sh && ./scripts/make-dmg.sh`  
   Or download from [Releases](https://github.com/Surya7612/Engram/releases) when uploaded.
2. Drag to Applications → right-click **Open** (ad-hoc) → grant **Screen Recording**.
3. Open [`website/fake-datadog.html`](../website/fake-datadog.html) (or `/site/fake-datadog.html` when API is up).
4. **Capture window & ask** (API defaults to hosted Engram).

Fallback: **Use demo fixture** in the app (no capture).

Details: [`ONCALL_COMPANION.md`](./ONCALL_COMPANION.md).

## Local builders

```bash
source .venv/bin/activate
ENGRAM_STORE=local OPENAI_API_KEY= python main.py seed
ENGRAM_STORE=local OPENAI_API_KEY= python main.py serve
# → http://127.0.0.1:8000/try

make situation   # CLI on-call fixture
make run         # Auth TTL agent loop
make eval        # V1.5 harness (local only; blocked on public Try)
```

Dual model: omit `OPENAI_API_KEY` for local-hash embeddings / template answers; set a key for stronger synthesis. Engram still owns retrieval, gates, and provenance.

## Learning loop (thin V3)

Reject → rerun is the shipped outcome loop (similar-task prior lookup). Not a trained routing policy.
