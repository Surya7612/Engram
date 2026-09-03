# Hosted Try

Public demo of Engram’s context → risk → governance loop. **Not** multi-tenant SaaS, **not** BYO clone/run on the shared host.

## Live URL

- **Try:** [https://engram-cjph.onrender.com/try](https://engram-cjph.onrender.com/try)
- Prefer `/try` (redirects to the Try UI). Avoid bookmarking `/site/try.html` alone if cold-start messaging confuses you—`/try` is the canonical entry.

## Demo script (2–3 minutes)

1. **Ingest** a public repo (default example works) → graph + vectors for that service  
2. **Query** / **Preflight** → evidence-backed answer and risk packet  
3. **Sample Auth — Run agents** on the TTL task → expect `block` (ADR-12)  
4. **Reject** with a note → **Run agents** again → prior surfaces as a constraint  

Side guide on the Try page explains each section. Nothing is merged or pushed.

## Public scope

| Enabled | Disabled |
|---|---|
| Public GitHub ingest (capped) | BYO clone / worktree run |
| Query + preflight | Eval harness (`POST /eval`) |
| Sample Auth / Email risk loop | Browser-supplied GitHub PATs |
| Outcome resolve (approve/reject record) | Multi-tenant isolation |

Env:

- Required for hosted: `ENGRAM_PUBLIC_MODE=true`, `ENGRAM_SEED_ON_BOOT=true`, `ENGRAM_STORE=local`
- Optional: `OPENAI_API_KEY` (better answers), server-side `GITHUB_TOKEN` (rate limits), `ENGRAM_CORS_ORIGINS` (Vercel marketing domain)

## Deploy (Render)

1. Push this repo to GitHub.  
2. Web Service from repo (Docker; see `Dockerfile` / `render.yaml`).  
3. Set the env vars above.  
4. Open `https://<service>.onrender.com/try`.

Free-tier cold starts can take a minute—use **Check API** if the first request fails.

## Vercel marketing

Keep `website/` on Vercel. CTAs should open the Render Try URL.

`website/config.js` sets `apiBase` to the Render host so a static Try page can still call the API (CORS must allow the Vercel origin).

## Local builder mode

```bash
ENGRAM_PUBLIC_MODE=false python main.py serve
# http://127.0.0.1:8000/try
```

Full clone/run and eval remain available locally. See [`README.md`](../README.md).
