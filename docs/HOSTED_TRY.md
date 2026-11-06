# Hosted Try

Public demo of Engram’s context → risk → governance loop. **Not** multi-tenant SaaS, **not** BYO clone/run on the shared host.

## Live URL

- **Try:** [https://engram-cjph.onrender.com/try](https://engram-cjph.onrender.com/try)
- Prefer `/try` (redirects to the Try UI). Canonical entry is `/try`, not a direct `/site/try.html` bookmark.

## Demo script (2–4 minutes)

Full locked script: [`DEMO.md`](./DEMO.md).

The hosted demo uses only the seeded sample organization:

1. Query / preflight Auth Service with source evidence.
2. On-call: load the payment-worker fixture and ask about the situation.
3. Run the sample Auth TTL risk loop; expect a block grounded in ADR-12.

Runs are ephemeral. Shared GitHub ingestion, sample reset, outcome listing and
approve/reject writes return 403. Ingest and the persistent learning loop remain
available on your own local/dev API. No anonymous text becomes a later visitor's prior.

Optional Mac companion (same `/situation` API): [DMG](https://github.com/Surya7612/Engram/releases) + [`ONCALL_COMPANION.md`](./ONCALL_COMPANION.md).

## Public scope

| Enabled | Disabled |
|---|---|
| Seeded query + preflight | Shared GitHub ingestion and sample reset |
| Ephemeral on-call situation | BYO clone/run, browser PATs, eval |
| Fixture-only Auth / Email risk loop | Shared outcome reads, resolution and persistent priors |

Env:

- Hosted: `ENGRAM_PUBLIC_MODE=true`, `ENGRAM_SEED_ON_BOOT=true`, `ENGRAM_STORE=local`.
- Remove `GITHUB_TOKEN` from the public service; it is unnecessary for this demo.
- Optional: `OPENAI_API_KEY` (answers), `ENGRAM_CORS_ORIGINS` (marketing domain).

On rollout, restart to rebuild graph/vector context from the trusted sample. Public
requests fail closed until seeding succeeds. Public runs ignore existing outcome
logs, do not record new outcomes, and never use repository metadata to clone.
Quarantine or remove old demo outcomes and clones through operator-controlled
maintenance; inspect GitHub token audit activity and rotate the previously exposed
service token. A code push alone does not establish that the running host is fixed.

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
