#!/usr/bin/env bash
# Runs on the target host (liquidweb1). Expects the release tarball already uploaded.
set -euo pipefail

APP_DIR="${ARTIST_APP_DIR:-/opt/artist}"
COMPOSE_PROJECT="${ARTIST_COMPOSE_PROJECT:-artist}"
HTTP_PORT="${ARTIST_HTTP_PORT:-80}"
HTTPS_PORT="${ARTIST_HTTPS_PORT:-8443}"
DOMAIN="${ARTIST_DOMAIN:-artist.northlayertech.com}"
RELEASE_TGZ="${ARTIST_RELEASE_TGZ:-/tmp/artist-release.tar.gz}"

public_https_url() {
  local path="${1:-/}"
  if [[ "${HTTPS_PORT}" == "443" ]]; then
    printf 'https://%s%s\n' "${DOMAIN}" "${path}"
  else
    printf 'https://%s:%s%s\n' "${DOMAIN}" "${HTTPS_PORT}" "${path}"
  fi
}

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
  if command_exists curl; then
    curl -fsS -o /dev/null "http://127.0.0.1:${HTTP_PORT}/"
  elif command_exists wget; then
    wget -q --spider "http://127.0.0.1:${HTTP_PORT}/"
  else
    docker exec artist wget -q --spider http://127.0.0.1:80/
  fi
}

ensure_docker
ensure_ports

mkdir -p "${APP_DIR}"
tmp_extract="$(mktemp -d)"
trap 'rm -rf "${tmp_extract}"' EXIT

tar -xzf "${RELEASE_TGZ}" -C "${tmp_extract}"

rsync -a --delete \
  --exclude '.env' \
  "${tmp_extract}/" "${APP_DIR}/" 2>/dev/null || {
  find "${APP_DIR}" -mindepth 1 -maxdepth 1 ! -name '.env' -exec rm -rf {} +
  tar -xzf "${RELEASE_TGZ}" -C "${APP_DIR}"
}

cd "${APP_DIR}"

{
  echo "ARTIST_IMAGE=artist"
  echo "ARTIST_TAG=latest"
  echo "ARTIST_CONTAINER_NAME=artist"
  echo "ARTIST_HTTP_PORT=${HTTP_PORT}"
  echo "ARTIST_HTTPS_PORT=${HTTPS_PORT}"
  echo "ARTIST_DOMAIN=${DOMAIN}"
  echo "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT}"
} > "${APP_DIR}/.env"
chmod 600 "${APP_DIR}/.env"

echo "Building and starting artist (${DOMAIN}) http:${HTTP_PORT} https:${HTTPS_PORT} ..."
docker_compose --env-file "${APP_DIR}/.env" -p "${COMPOSE_PROJECT}" up -d --build --force-recreate

echo "Waiting for health..."
for _ in $(seq 1 60); do
  if http_ok; then
    echo "Sergei Kasabov site is up:"
    echo "  $(public_https_url /)"
    echo "  http://${DOMAIN}/  (ACME + redirect when cert is ready)"
    docker_compose --env-file "${APP_DIR}/.env" -p "${COMPOSE_PROJECT}" ps
    exit 0
  fi
  sleep 2
done

echo "Container started but HTTP check failed." >&2
docker_compose --env-file "${APP_DIR}/.env" -p "${COMPOSE_PROJECT}" logs --tail=120 || true
exit 1
