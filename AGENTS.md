# Agent notes

## Production

- Push to `main` runs `.github/workflows/deploy.yml` (`Deploy Artist`) to Liquid Web `liquidweb1` (`69.16.249.191` from doors inventory).
- The `test` job (static file checks + `python -m compileall -q api/app`) must pass before `deploy`.
- Public site: `https://kasabov.northlayertech.com:8443/` (host `:443` is OpenVPN stunnel).
- Admin: `https://kasabov.northlayertech.com:8443/admin.html`
- DNS A record for `kasabov.northlayertech.com` must point at `69.16.249.191`.
- Repo secret required: `SSH_DEPLOY_KEY` (ed25519 private key with root access on liquidweb1).
- Host `.env` holds `ADMIN_USER`, `ADMIN_PASSWORD_HASH`, `SECRET_KEY` (preserved across deploys).

## Tests

No unit suite. CI verifies release files exist and compiles the API:

```text
index.html admin.html admin.js styles.css main.js i18n.js works-data.js Dockerfile docker-compose.yml docker/Caddyfile seed/manifest.json assets/studio api/app
python -m compileall -q api/app
```

Do not invent a test framework. Add tests only when the plan asks for them.

## Lint

none

## Typecheck

none

## Dependency audit

none

## Migrations

none

## Post-deploy check

Read-only HTTP GET `https://kasabov.northlayertech.com:8443/` (or `http://kasabov.northlayertech.com/` if TLS is not ready). A non-success status is `FAIL`. Do not log into admin. Do not SSH to change server files.

## Rollback

Disabled. Do not revert. Git history is the record; a person rolls back if they want to.
