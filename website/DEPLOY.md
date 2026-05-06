# Engram Website Deployment Guide

This guide covers end-to-end deployment for both Vercel and Netlify.

## Before you deploy

1. Confirm local preview:
   ```bash
   cd website
   python3 -m http.server 8080
   ```
2. Open `http://localhost:8080` and verify:
   - dark/light mode works
   - hero interactions work
   - request access modal + form submit works
3. Ensure email intake is active on `formsubmit.co` for `nsurya@havenlyai.com`.

---

## Option A: Vercel (recommended)

### Via Dashboard

1. Go to [vercel.com](https://vercel.com) and create/import project from this repo.
2. In **Root Directory**, set: `website`
3. Framework preset: **Other**
4. Build command: leave empty
5. Output directory: `.` (or empty for static root)
6. Deploy.

`vercel.json` in this folder already configures:
- clean URLs
- security headers
- asset caching headers

### Via CLI

```bash
cd website
npm i -g vercel
vercel login
vercel
vercel --prod
```

When prompted:
- Link to existing project: your choice
- Root directory: current (`website`)

---

## Option B: Netlify

### Via Dashboard

1. Go to [netlify.com](https://netlify.com), add new site from Git.
2. Set **Base directory**: `website`
3. Build command: leave empty
4. Publish directory: `.`
5. Deploy site.

`netlify.toml` already includes:
- security headers
- static asset cache headers

### Via CLI

```bash
cd website
npm i -g netlify-cli
netlify login
netlify init
netlify deploy
netlify deploy --prod
```

For prompts:
- Publish directory: `.`
- Functions: none

---

## Post-deploy checks

Run these checks on the live URL:

1. Navigation anchors scroll correctly.
2. All CTA buttons open the access modal.
3. Form submit returns success message.
4. Theme toggle persists after refresh.
5. Mobile layout is clean and readable.
6. No console errors in browser dev tools.

---

## Custom domain (optional)

- Add your domain in platform settings (`engram.ai`).
- Update DNS records as instructed by Vercel/Netlify.
- Re-test form submission from live domain.
