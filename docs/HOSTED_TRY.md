# Hosted Try (resume / recruiter demo)

Tight public scope — not multi-tenant SaaS, not BYO clone/run on the shared host.

## What recruiters can do

On the **API host** (same origin Try UI at `/try`):

1. Ingest a **public** GitHub repo (capped, default 30 PRs)
2. Query / preflight on that service
3. Sample Auth risk loop (seeded on boot): run → reject → run again

Disabled in `ENGRAM_PUBLIC_MODE=true`: eval harness, BYO clone worktrees, browser-supplied GitHub PATs.

## Deploy API (Render example)

1. Push this repo to GitHub.
2. Create a Render Web Service from the repo (Docker).
3. Set env:
   - `ENGRAM_PUBLIC_MODE=true`
   - `ENGRAM_SEED_ON_BOOT=true`
   - `ENGRAM_CORS_ORIGINS=https://YOUR-VERCEL-DOMAIN` (comma-separated if multiple)
   - Optional: `OPENAI_API_KEY`, `GITHUB_TOKEN` (server-side rate limits / better answers)
4. After deploy, open `https://YOUR-RENDER-HOST/try`.

`render.yaml` is a starting point.

## Vercel marketing site

Keep `website/` on Vercel. Point CTAs to the Render Try URL.

Optional: set `website/config.js`:

```js
window.ENGRAM_CONFIG = {
  apiBase: "https://YOUR-RENDER-HOST",
};
```

If recruiters use Render `/try` directly, `apiBase` can stay empty (same origin).

## Local builder mode

```bash
ENGRAM_PUBLIC_MODE=false python main.py serve
```

Full clone/run and eval remain available locally.
