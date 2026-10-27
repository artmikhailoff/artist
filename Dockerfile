FROM caddy:2.8-alpine

COPY docker/Caddyfile /etc/caddy/Caddyfile
COPY index.html /srv/index.html
COPY styles.css /srv/styles.css
COPY main.js /srv/main.js
COPY i18n.js /srv/i18n.js
COPY works-data.js /srv/works-data.js
COPY assets/ /srv/assets/

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:80/ || exit 1
