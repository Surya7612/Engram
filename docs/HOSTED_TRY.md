# Hosted Try

Public demo of Engram’s context → risk → governance loop. **Not** multi-tenant SaaS, **not** BYO clone/run on the shared host.

## Live URL

- **Try:** [https://engram-cjph.onrender.com/try](https://engram-cjph.onrender.com/try)
- Prefer `/try` (redirects to the Try UI). Canonical entry is `/try`, not a direct `/site/try.html` bookmark.

## Demo script (2–4 minutes)

Full locked script: [`DEMO.md`](./DEMO.md).

1. **Ingest** a public repo (default example works) → graph + vectors for that service  
2. **Query** / **Preflight** → evidence-backed answer and risk packet  
3. **On-call situation** → load payment-worker fixture → Ask situation (same `POST /situation` as the Mac companion)  
4. **Sample Auth — Run agents** on the TTL task → expect `block` (ADR-12)  
5. **Reject** with a note → **Run agents** again → prior surfaces as a constraint  

Side guide on the Try page explains each section. Nothing is merged or pushed.

Optional Mac path: download the [companion DMG](https://github.com/Surya7612/Engram/releases), grant Screen Recording, open `/site/fake-datadog.html`, **Capture window & ask**. Details: [`ONCALL_COMPANION.md`](./ONCALL_COMPANION.md).

## Public scope

| Enabled | Disabled |
|---|---|
| Public GitHub ingest (capped) | BYO clone / worktree run |
| Query + preflight | Eval harness (`POST /eval`) |
| On-call situation (`POST /situation`) | Browser-supplied GitHub PATs |
| Sample Auth / Email risk loop | Multi-tenant isolation |
| Outcome resolve (approve/reject record) | |

Env:

- Required for hosted: `ENGRAM_PUBLIC_MODE=true`, `ENGRAM_SEED_ON_BOOT=true`, `ENGRAM_STORE=local`
- Optional: `OPENAI_API_KEY` (better answers), server-side `GITHUB_TOKEN` (rate limits), `ENGRAM_CORS_ORIGINS` (Vercel marketing domain)

## Deploy (Render)

1. Push this repo to GitHub.  
2. Web Service from repo (Docker; see `Dockerfile` / `render.yaml`).  
3. Set the env vars above.  
4. Open `https://<service>.onrender.com/try`.

If the service sticks on Render’s “Application loading” page after a push, open the
Render dashboard → **Manual Deploy** → **Deploy latest commit**. Auto-deploy alone
is not enough when a prior boot hung on seed/embeddings (free tier will keep the
old unhealthy instance until a new deploy lands).

Optional: add a Render **Deploy Hook** URL as GitHub secret `RENDER_DEPLOY_HOOK`
so `.github/workflows/deploy-hosted.yml` can trigger rebuilds on API changes.

Free-tier cold starts can take ~1 minute while Render allocates a machine. The API
binds before demo seeding finishes (`GET /live`, `GET /meta` include `seeded`).
A GitHub Action pings `/live` every 10 minutes to reduce spin-downs. Use **Check API**
if the first browser request still lands on Render’s wake page.

Public mode uses local-hash embeddings so boot never waits on OpenAI; chat can still
use `OPENAI_API_KEY` when set.

## Vercel marketing

Keep `website/` on Vercel. CTAs should open the Render Try URL.

`website/config.js` sets `apiBase` to the Render host so a static Try page can still call the API (CORS must allow the Vercel origin).

## Local development

```bash
ENGRAM_PUBLIC_MODE=false python main.py serve
# http://127.0.0.1:8000/try
```

Full clone/run and eval remain available locally. See [`README.md`](../README.md).
