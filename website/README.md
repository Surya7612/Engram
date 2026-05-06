# Engram Website

## Quick run

Open `index.html` directly in a browser for a fast preview.

For best module loading behavior, serve the folder with a local static server:

```bash
cd website
python3 -m http.server 8080
```

Then open `http://localhost:8080`.

## Production checklist

- Verify all CTA flows open the access modal.
- Submit the access form once to activate `formsubmit.co` delivery.
- Test dark and light theme contrast on desktop/mobile.
- Confirm hero live statuses animate every few seconds.
- Run Lighthouse quick pass for performance and accessibility.

## Deploy

- **Vercel:** import `website/` as root project (uses `vercel.json`).
- **Netlify:** set publish directory to `website/` (uses `netlify.toml`).
- Full step-by-step: see `DEPLOY.md`.
