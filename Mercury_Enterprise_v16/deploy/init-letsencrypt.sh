#!/usr/bin/env sh
# Obtain an initial Let's Encrypt certificate for Mercury production NGINX.
# Prerequisites: DNS for DOMAIN points to this host; ports 80/443 open.
# Usage (from package root):
#   export DOMAIN=mercury.example.com LETSENCRYPT_EMAIL=ops@example.com
#   sh deploy/init-letsencrypt.sh
#
# Always include docker-compose.production.yml so host :3000 stays unpublished
# during ACME bootstrap. Override COMPOSE only if you know you need another file set.
# POSTGRES_PASSWORD must already be in .env (the overlay refuses the LAN default).

set -eu

DOMAIN="${DOMAIN:?DOMAIN is required}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:?LETSENCRYPT_EMAIL is required}"
COMPOSE="${COMPOSE:-docker compose -f docker-compose.yml -f docker-compose.production.yml}"
STAGING="${STAGING:-0}"

STAGING_ARG=""
if [ "$STAGING" = "1" ]; then
  STAGING_ARG="--staging"
fi

echo "Creating dummy certificate for ${DOMAIN} so NGINX can start..."
$COMPOSE --profile production run --rm --entrypoint "\
  mkdir -p /etc/letsencrypt/live/${DOMAIN} && \
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /etc/letsencrypt/live/${DOMAIN}/privkey.pem \
    -out /etc/letsencrypt/live/${DOMAIN}/fullchain.pem \
    -subj /CN=${DOMAIN}" certbot

echo "Starting edge NGINX..."
$COMPOSE --profile production up -d nginx

echo "Requesting Let's Encrypt certificate..."
$COMPOSE --profile production run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  $STAGING_ARG \
  -d "$DOMAIN" \
  --email "$LETSENCRYPT_EMAIL" \
  --agree-tos \
  --no-eff-email \
  --force-renewal

echo "Reloading NGINX with real certificate..."
$COMPOSE --profile production exec nginx nginx -s reload

echo "Done. Verify: https://${DOMAIN}/ready"
