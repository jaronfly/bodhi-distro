# Bodhi landing page

The public page for **Bodhi, the seed**. One static page, no build step, no framework, no tracking.

```
site/
  index.html            the whole story, readable with JavaScript off
  styles.css            brand tokens, layout, scrims, reduced-motion rules
  app.js                progressive enhancement: seed animation, padded cell, tree, sky, ancestral plane,
                        the summary that unpacks, motion switch, copy buttons
  assets/
    data/ancestry.js    987 commit kinds and dates for the ancestral plane (extracted from the research DATA)
    receipts/           the seven exhibit screenshots, WebP + JPEG, 800 px and full size
    marks/              Random Universe marks; jf.svg goes here when it exists
    favicon.svg         the mark on soil, whole pixels
    og.png              1200x630 social preview
  journey/              NOT in this branch: the 3D journey layer, built separately and merged by the lead
  README.md             this file
  REVIEW.md             the owner's checklist before this goes public
```

Every URL in the page is relative, so the folder works at a domain root, a subdomain or any subpath.

## Preview locally

```sh
cd site
python3 -m http.server 8000
# open http://localhost:8000
```

Until `site/journey/` is merged, the browser logs one 404 for `journey/journey.js`, and one for `assets/marks/jf.svg` until that file exists. Both are expected; the page falls back to its own 2D art and to the text "Jaron Flynn".

## Deploy as a subdomain

Pick one host. In each case the thing to publish is the `site/` folder as-is.

### Cloudflare Pages

1. Pages → Create a project → connect the repository (or use Direct Upload with the `site/` folder).
2. Framework preset: none. Build command: leave empty. Build output directory: `site`.
3. Custom domains → add `bodhi.example.com` (your subdomain). If the parent domain's DNS is on Cloudflare, it creates the record for you; otherwise add a `CNAME bodhi → <project>.pages.dev` at your DNS host.

### Netlify

1. Add new site → import the repository (or drag the `site/` folder onto the Deploys page).
2. Build command: empty. Publish directory: `site`.
3. Domain management → add the subdomain, then create `CNAME bodhi → <site-name>.netlify.app` at your DNS host.

### GitHub Pages

Pages serves a branch root or `/docs`, so a `site/` folder needs a small Actions workflow (kept out of this branch on purpose; the lead decides where workflows live):

```yaml
# .github/workflows/pages.yml
on: { push: { branches: [main] }, workflow_dispatch: {} }
permissions: { contents: read, pages: write, id-token: write }
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: { name: github-pages }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/upload-pages-artifact@v3
        with: { path: site }
      - uses: actions/deploy-pages@v4
```

Then Settings → Pages → Source: GitHub Actions, and Custom domain: your subdomain, with `CNAME bodhi → <user>.github.io` at your DNS host. GitHub Pages for a private repository needs a paid plan; for a public repository it is free.

### Any other static host

Upload the contents of `site/`. Serve `index.html` as the default document. Nothing else is required: no rewrites, no server code, no environment variables.

## After the first deploy

- Change `og:image` in `index.html` to the absolute URL (`https://<subdomain>/assets/og.png`). Social cards need an absolute URL.
- Replace the placeholders listed in `REVIEW.md`.
- Suggested caching: `assets/*` for a year, `index.html`, `styles.css` and `app.js` for a few minutes (or add a version query when you change them).

## How the page behaves

- **No JavaScript**: every word, quote, note and receipt is in the HTML. The lockup is a static SVG; canvases and dead buttons are hidden.
- **Reduced motion** (system setting) or the header's **Motion** switch (`html[data-motion="off"]`): every scene renders one complete still frame. The switch also dispatches a `bodhi:motion` event for the journey layer.
- **The journey layer**: `#journey` is a fixed, pointer-transparent 3D stage behind the page. When it renders it adds `html.journey-on`, and the decorative 2D canvases (tree, sky, ancestral plane) and scene fills step aside while text sits on Soil scrims. The padded cell and the seed marks always stay. If the 3D layer never loads, the 2D art is the page.
- **Pixel art**: every canvas draws one canvas pixel per art pixel and scales by a whole number with `image-rendering: pixelated`. The mark and wordmark come from the brand's exact paths and are never retyped.

## Updating the receipts

The exhibit images and captions come from *The Bodhi Build* (draft v0.3, 2026-09-28). To replace one, export WebP and JPEG at full size and at 800 px wide with the same file names, keep the caption word for word, and check it for private details first (see `REVIEW.md`). The commit data in `assets/data/ancestry.js` came from the same report by script; regenerate it rather than editing it by hand.
