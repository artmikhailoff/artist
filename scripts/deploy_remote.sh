#!/usr/bin/env bash
# Runs on the target host (liquidweb1). Expects the release tarball already uploaded.
set -euo pipefail

APP_DIR="${ARTIST_APP_DIR:-/opt/artist}"
COMPOSE_PROJECT="${ARTIST_COMPOSE_PROJECT:-artist}"
HTTP_PORT="${ARTIST_HTTP_PORT:-80}"
HTTPS_PORT="${ARTIST_HTTPS_PORT:-8443}"
DOMAIN="${ARTIST_DOMAIN:-kasabov.northlayertech.com}"
RELEASE_TGZ="${ARTIST_RELEASE_TGZ:-/tmp/artist-release.tar.gz}"

public_https_url() {
  local path="${1:-/}"
  if [[ "${HTTPS_PORT}" == "443" ]]; then
    printf 'https://%s%s\n' "${DOMAIN}" "${path}"
  else
    printf 'https://%s:%s%s\n' "${DOMAIN}" "${HTTPS_PORT}" "${path}"
  fi
}

# Default bcrypt for initial bootstrap only (rotate via ADMIN_PASSWORD_HASH in .env).
# Plain password is never stored on disk by this script.
DEFAULT_ADMIN_USER="kasabov"
DEFAULT_ADMIN_PASSWORD_HASH='$2b$12$m/0bq/bwpMWfsjqlrq3hW.ckAlVwMidzNiN5GXfYr5swfYgdiNYVq'

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

run_as_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  elif command_exists sudo; then
    sudo -n "$@"
  else
    echo "Need root to install Docker / open firewall: $*" >&2
    exit 1
  fi
}

ensure_docker() {
  if command_exists docker && docker compose version >/dev/null 2>&1; then
    return
  fi

  if ! command_exists apt-get; then
    echo "Docker is missing and apt-get is unavailable." >&2
    exit 1
  fi

  echo "Installing Docker..."
  run_as_root apt-get update -y
  run_as_root apt-get install -y docker.io docker-compose-plugin || \
    run_as_root apt-get install -y docker.io docker-compose
  if command_exists systemctl; then
    run_as_root systemctl enable --now docker
  fi
}

ensure_ports() {
  if command_exists ufw && ufw status 2>/dev/null | grep -qi "Status: active"; then
    echo "Allowing TCP ${HTTP_PORT}/tcp and ${HTTPS_PORT}/tcp in UFW (idempotent)."
    run_as_root ufw allow "${HTTP_PORT}/tcp" comment "artist-http" || true
    run_as_root ufw allow "${HTTPS_PORT}/tcp" comment "artist-https" || true
  fi
}

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

http_ok() {
  local health_url="http://127.0.0.1:${HTTP_PORT}/healthz"
  if command_exists curl; then
    curl -fsS -o /dev/null -H "Host: ${DOMAIN}" "${health_url}"
  elif command_exists wget; then
    wget -q --spider --header "Host: ${DOMAIN}" "${health_url}"
  else
    docker exec artist wget -q --spider --header "Host: ${DOMAIN}" http://127.0.0.1:80/healthz
  fi
}

env_get() {
  local key="$1"
  local file="$2"
  if [[ -f "${file}" ]]; then
    local line
    line="$(grep -E "^${key}=" "${file}" | tail -n1 || true)"
    if [[ -n "${line}" ]]; then
      printf '%s\n' "${line#*=}" | sed 's/\$\$/$/g'
      return 0
    fi
  fi
  return 1
}

compose_escape() {
  printf '%s' "$1" | sed 's/\$/$$/g'
}

ensure_docker
ensure_ports

mkdir -p "${APP_DIR}"
tmp_extract="$(mktemp -d)"
trap 'rm -rf "${tmp_extract}"' EXIT

tar -xzf "${RELEASE_TGZ}" -C "${tmp_extract}"

# Preserve host .env (secrets + admin credentials) across code sync.
rsync -a --delete \
  --exclude '.env' \
  "${tmp_extract}/" "${APP_DIR}/" 2>/dev/null || {
  find "${APP_DIR}" -mindepth 1 -maxdepth 1 ! -name '.env' -exec rm -rf {} +
  tar -xzf "${RELEASE_TGZ}" -C "${APP_DIR}"
}

cd "${APP_DIR}"

EXISTING_ENV="${APP_DIR}/.env"
SECRET_KEY="$(env_get SECRET_KEY "${EXISTING_ENV}" || true)"
ADMIN_USER="$(env_get ADMIN_USER "${EXISTING_ENV}" || true)"
ADMIN_PASSWORD_HASH="$(env_get ADMIN_PASSWORD_HASH "${EXISTING_ENV}" || true)"

if [[ -z "${SECRET_KEY}" ]]; then
  if command_exists openssl; then
    SECRET_KEY="$(openssl rand -hex 32)"
  else
    SECRET_KEY="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  fi
fi

if [[ -z "${ADMIN_USER}" ]]; then
  ADMIN_USER="${DEFAULT_ADMIN_USER}"
fi

if [[ -z "${ADMIN_PASSWORD_HASH}" ]]; then
  ADMIN_PASSWORD_HASH="${DEFAULT_ADMIN_PASSWORD_HASH}"
fi

{
  echo "ARTIST_IMAGE=artist"
  echo "ARTIST_API_IMAGE=artist-api"
  echo "ARTIST_TAG=latest"
  echo "ARTIST_CONTAINER_NAME=artist"
  echo "ARTIST_API_CONTAINER_NAME=artist-api"
  echo "ARTIST_HTTP_PORT=${HTTP_PORT}"
  echo "ARTIST_HTTPS_PORT=${HTTPS_PORT}"
  echo "ARTIST_DOMAIN=${DOMAIN}"
  echo "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT}"
  echo "COOKIE_SECURE=true"
  printf 'SECRET_KEY=%s\n' "$(compose_escape "${SECRET_KEY}")"
  printf 'ADMIN_USER=%s\n' "$(compose_escape "${ADMIN_USER}")"
  printf 'ADMIN_PASSWORD_HASH=%s\n' "$(compose_escape "${ADMIN_PASSWORD_HASH}")"
} > "${APP_DIR}/.env"
chmod 600 "${APP_DIR}/.env"

echo "Building and starting artist (${DOMAIN}) http:${HTTP_PORT} https:${HTTPS_PORT} ..."
docker_compose --env-file "${APP_DIR}/.env" -p "${COMPOSE_PROJECT}" up -d --build --force-recreate

echo "Waiting for health..."
for _ in $(seq 1 90); do
  if http_ok; then
    echo "Sergei Kasabov site is up:"
    echo "  $(public_https_url /)"
    echo "  http://${DOMAIN}/  (ACME + redirect when cert is ready)"
    echo "  admin: $(public_https_url /admin.html)"
    docker_compose --env-file "${APP_DIR}/.env" -p "${COMPOSE_PROJECT}" ps
    exit 0
  fi
  sleep 2
done

echo "Container started but HTTP check failed." >&2
docker_compose --env-file "${APP_DIR}/.env" -p "${COMPOSE_PROJECT}" logs --tail=120 || true
exit 1
