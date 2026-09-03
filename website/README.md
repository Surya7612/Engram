# Engram Website

Marketing surface for Engram. The interactive demo runs on the **API host**, not as a standalone static backend.

## Live Try

[https://engram-cjph.onrender.com/try](https://engram-cjph.onrender.com/try)

Marketing CTAs on `index.html` should open that URL. `config.js` sets `apiBase` for the same host.

## Quick run (marketing only)

```bash
cd website
python3 -m http.server 8080
```

Then open `http://localhost:8080`. Static Try without a reachable API will show a connection banner—use the Render `/try` URL or `python main.py serve` from the repo root.

## Production checklist

- Try / nav CTAs open the hosted Try URL.
- Access form still works for early-access requests.
- Dark and light theme contrast on desktop/mobile.
- After CSS/JS edits, bump `?v=` query params.

## Deploy

- **Vercel:** import `website/` as root (uses `vercel.json`). Set `ENGRAM_CORS_ORIGINS` on Render to the Vercel domain if static pages call the API.
- **API / Try:** Docker on Render — see [`docs/HOSTED_TRY.md`](../docs/HOSTED_TRY.md).
- More: `DEPLOY.md`.
