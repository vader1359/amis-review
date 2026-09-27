# PSI preview UI

React + Ant Design 6, bundled locally. The Python preview serves the checked-in build in `web/preview_static/`; no CDN or Node runtime is needed to use it.

From the repository root:

```sh
npm ci --prefix web/ui
npm --prefix web/ui test
npm --prefix web/ui run build
```

The build outputs only `/app.js`, `/styles.css`, and `/index.html`. Keep the generated files with source changes. `GET /api/config` must return `preview_token`, `style_nonce`, and `saved_sources`. The UI waits for that nonce before mounting Ant Design.

Periodic uploads are classified as one batch and remain in memory for the current page. Reusable source cards explicitly save or replace server-held selections. Saved IDs are sent to `/api/drafts`; generated Drafts never automatically become the saved prior Final.
