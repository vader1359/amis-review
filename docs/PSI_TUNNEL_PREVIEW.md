# PSI preview on Ian's Win

The preview runs in Ubuntu WSL on Ian's Win, independently of the Mac.
Cloudflare Quick Tunnel provides a free, random HTTPS hostname. It is a preview
address, not a permanent domain, and can change when the tunnel restarts.

## Runtime

- Private installation: `/home/iant1359/.local/share/psi-preview`.
- Release: `releases/20260906-preview`; Python 3.14.6 and locked online dependencies.
- User services: `psi-preview-gateway.service` and `psi-quick-tunnel.service`.
- Gateway binds only `127.0.0.1:18788`, using `uvicorn --no-proxy-headers`.
- Cloudflared uses HTTP/2 and forwards to that loopback endpoint.
- The public shell displays an Ant Design login form. Report data and mutations
  require a signed 12-hour Secure, HttpOnly, SameSite=Strict session cookie.
  HTTP Basic remains supported for API clients; no native browser challenge is sent.
- Anonymous `/api/config` returns only the login flag and style nonce.
- `private/access.json` contains `username`, `password`, and the exact
  `public_host` hostname. Keep this and `private/runtime.env` mode 0600.
- `PSI_REPORT_DATABASE_URL` retains the restricted Neon role and verified TLS.
- `PSI_SOURCE_STORE_DIR` points to `saved-sources`; approved sources are retained.
- `PSI_REPORT_ARTIFACT_DIR` points to `artifacts`, a private 0700 directory.
  Immutable `<sha256>.xlsx` originals are verified against the database payload,
  workbook validator and snapshot before downloads, including across platforms.

## Operation

Windows and Ubuntu WSL must remain running and connected. Both services are enabled
for the WSL user's systemd session. Windows boot startup and user linger were not
configured; do not assume availability after Windows restarts or sleeps.

Inspect the two user services with `systemctl --user status`. The tunnel URL is
recorded in `logs/tunnel.log`. If the tunnel restarts with a new hostname, update
only `public_host` in the private JSON and restart `psi-preview-gateway.service`.
The gateway deliberately rejects a new hostname until its configuration matches.
Do not put passwords in URLs, command arguments, logs, or version control.

Stop public access with `systemctl --user stop psi-quick-tunnel.service`.
The private Neon reports and retained source files remain intact.

## Acceptance evidence

47 focused gateway and artifact-store tests passed, with independent code review.
Live external checks returned 200 for the login shell, 401 for private APIs
without authentication, 200 with credentials,
and 403 for a foreign Origin. Four retained source files and 17 historical sheets
were visible. Download of the original report matched SHA-256
`c8bb2fac04f254aaf32aef04249df314297e68e182363bf5602a73bc2c98ac44`.
Local private evidence is in `.agents/psi-ian-win-public-qa.json`.

Reference: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/
