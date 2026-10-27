# Agent notes

## Production

- Push to `main` runs `.github/workflows/deploy.yml` (`Deploy Artist`) to Liquid Web `liquidweb1` (`69.16.249.191` from doors inventory).
- The `test` job (static file checks) must pass before `deploy`.
- Public site: `https://artist.northlayertech.com:8443/` (host `:443` is OpenVPN stunnel).
- DNS A record for `artist.northlayertech.com` must point at `69.16.249.191`.
- Repo secret required: `SSH_DEPLOY_KEY` (ed25519 private key with root access on liquidweb1).

## Tests

No unit suite. CI verifies release files exist:

```text
index.html styles.css main.js i18n.js works-data.js Dockerfile docker-compose.yml docker/Caddyfile assets/studio
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

Read-only HTTP GET `https://artist.northlayertech.com:8443/` (or `http://artist.northlayertech.com/` if TLS is not ready). A non-success status is `FAIL`. Do not SSH to change server files.

## Rollback

Disabled. Do not revert. Git history is the record; a person rolls back if they want to.
