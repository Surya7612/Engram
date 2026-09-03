# Hosted Try

Tight public scope — not multi-tenant SaaS, not BYO clone/run on the shared host.

## Live demo

- Try UI: [https://engram-cjph.onrender.com/try](https://engram-cjph.onrender.com/try)
- Prefer `/try` (not `/site/try.html`).

## What visitors can do

On the **API host** (same origin Try UI at `/try`):

1. Ingest a **public** GitHub repo (capped, default 30 PRs)
2. Query / preflight on that service
3. Sample Auth risk loop (seeded on boot): run → reject → run again

Disabled in `ENGRAM_PUBLIC_MODE=true`: eval harness, BYO clone worktrees, browser-supplied GitHub PATs.

Optional env: `OPENAI_API_KEY` (better answers), server-side `GITHUB_TOKEN` (rate limits). Browser PATs stay off in public mode.

## Deploy API (Render example)

1. Push this repo to GitHub.
2. Create a Render Web Service from the repo (Docker).
3. Set env:
   - `ENGRAM_PUBLIC_MODE=true`
   - `ENGRAM_SEED_ON_BOOT=true`
   - `ENGRAM_CORS_ORIGINS=https://YOUR-VERCEL-DOMAIN` (comma-separated if multiple)
   - Optional: `OPENAI_API_KEY`, `GITHUB_TOKEN`
4. After deploy, open `https://YOUR-RENDER-HOST/try`.

`render.yaml` is a starting point.

## Vercel marketing site

Keep `website/` on Vercel. Point CTAs to the Render Try URL (`https://engram-cjph.onrender.com/try`).

`website/config.js` sets `apiBase` to that host so a static Try page can still call the API.

## Local builder mode

```bash
ENGRAM_PUBLIC_MODE=false python main.py serve
```

Full clone/run and eval remain available locally.
